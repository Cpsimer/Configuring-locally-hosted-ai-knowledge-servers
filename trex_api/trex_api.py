#!/usr/bin/env python3
"""
T-Rex Taxonomy Classification API
Serves fine-tuned BERT model for Obsidian note classification
"""

from flask import Flask, request, jsonify
import numpy as np
import logging
from typing import List, Dict
import os

# Initialize Flask app
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model/client variables
triton_client = None
tokenizer = None
label_map = {}

def initialize_triton_client():
    """Initialize Triton client connection"""
    global triton_client, tokenizer, label_map
    
    try:
        import tritonclient.http as httpclient
        from transformers import AutoTokenizer
        
        triton_url = os.getenv('TRITON_URL', 'triton_server:8002')
        model_name = os.getenv('MODEL_NAME', 'trex_taxonomy')
        
        triton_client = httpclient.InferenceServerClient(url=triton_url)
        tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        
        # Load label mapping
        label_file = '/models/trex/labels.txt'
        if os.path.exists(label_file):
            with open(label_file, 'r') as f:
                label_map = {i: line.strip() for i, line in enumerate(f)}
        else:
            logger.warning("Label file not found, using dummy labels")
            label_map = {i: f"label_{i}" for i in range(50)}
        
        logger.info(f"Initialized Triton client for {model_name}")
        
    except Exception as e:
        logger.error(f"Failed to initialize Triton: {e}")
        logger.info("Falling back to dummy mode")

def classify_text_triton(text: str, threshold: float = 0.5) -> List[str]:
    """
    Classify text using Triton Inference Server
    
    Args:
        text: Input text to classify
        threshold: Confidence threshold for predictions
        
    Returns:
        List of predicted labels
    """
    try:
        import tritonclient.http as httpclient
        
        # Tokenize input
        inputs = tokenizer(
            text,
            max_length=512,
            truncation=True,
            padding='max_length',
            return_tensors='np'
        )
        
        # Prepare Triton inputs
        triton_inputs = [
            httpclient.InferInput(
                'input_ids',
                inputs['input_ids'].shape,
                'INT64'
            ),
            httpclient.InferInput(
                'attention_mask',
                inputs['attention_mask'].shape,
                'INT64'
            )
        ]
        
        triton_inputs[0].set_data_from_numpy(inputs['input_ids'].astype(np.int64))
        triton_inputs[1].set_data_from_numpy(inputs['attention_mask'].astype(np.int64))
        
        # Inference
        response = triton_client.infer(
            model_name='trex_taxonomy',
            inputs=triton_inputs
        )
        
        logits = response.as_numpy('logits')[0]
        
        # Apply sigmoid for multi-label
        probabilities = 1 / (1 + np.exp(-logits))
        
        # Get predictions above threshold
        predictions = np.where(probabilities > threshold)[0]
        labels = [label_map[i] for i in predictions if i in label_map]
        
        return labels
        
    except Exception as e:
        logger.error(f"Triton inference failed: {e}")
        return []

def classify_text_dummy(text: str) -> List[str]:
    """Dummy classifier for testing without Triton"""
    # Simple heuristic-based classification
    tags = []
    
    # Kind classification
    if any(word in text.lower() for word in ['train', 'model', 'epoch', 'loss']):
        tags.append('kind:ml_experiment')
    elif any(word in text.lower() for word in ['commit', 'merge', 'branch']):
        tags.append('kind:code_commit')
    elif any(word in text.lower() for word in ['meeting', 'discuss', 'agenda']):
        tags.append('kind:meeting_note')
    else:
        tags.append('kind:general')
    
    # PARA classification
    if any(word in text.lower() for word in ['deadline', 'deliverable', 'milestone']):
        tags.append('para:Projects')
    elif any(word in text.lower() for word in ['routine', 'process', 'standard']):
        tags.append('para:Areas')
    else:
        tags.append('para:Resources')
    
    # Topic tags
    if 'neural' in text.lower() or 'deep learning' in text.lower():
        tags.append('deep-learning')
    if 'docker' in text.lower() or 'container' in text.lower():
        tags.append('docker')
    if 'obsidian' in text.lower():
        tags.append('knowledge-management')
    
    return tags

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'triton_available': triton_client is not None
    }), 200

@app.route('/classify', methods=['POST'])
def classify():
    """
    Classify note content
    
    Request JSON:
        {
            "text": "Note content...",
            "threshold": 0.5 (optional)
        }
    
    Response JSON:
        {
            "suggested_tags": ["tag1", "tag2", ...],
            "confidence": 0.85
        }
    """
    try:
        data = request.json
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text field'}), 400
        
        text = data['text']
        threshold = data.get('threshold', 0.5)
        
        # Classify
        if triton_client:
            tags = classify_text_triton(text, threshold)
        else:
            tags = classify_text_dummy(text)
        
        # Extract PARA suggestion
        para_tags = [t for t in tags if t.startswith('para:')]
        para_suggestion = para_tags[0].replace('para:', '') if para_tags else 'Resources'
        
        # Extract kind suggestion
        kind_tags = [t for t in tags if t.startswith('kind:')]
        kind_suggestion = kind_tags[0].replace('kind:', '') if kind_tags else 'note'
        
        return jsonify({
            'suggested_tags': [t for t in tags if not t.startswith(('para:', 'kind:'))],
            'para_placement': para_suggestion,
            'kind': kind_suggestion,
            'all_predictions': tags,
            'model': 'triton' if triton_client else 'dummy'
        }), 200
        
    except Exception as e:
        logger.error(f"Classification error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/batch_classify', methods=['POST'])
def batch_classify():
    """
    Batch classification endpoint
    
    Request JSON:
        {
            "texts": ["text1", "text2", ...],
            "threshold": 0.5 (optional)
        }
    """
    try:
        data = request.json
        
        if not data or 'texts' not in data:
            return jsonify({'error': 'Missing texts field'}), 400
        
        texts = data['texts']
        threshold = data.get('threshold', 0.5)
        
        results = []
        for text in texts:
            if triton_client:
                tags = classify_text_triton(text, threshold)
            else:
                tags = classify_text_dummy(text)
            
            results.append({
                'tags': tags,
                'para': next((t.replace('para:', '') for t in tags if t.startswith('para:')), 'Resources')
            })
        
        return jsonify({'results': results}), 200
        
    except Exception as e:
        logger.error(f"Batch classification error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/labels', methods=['GET'])
def get_labels():
    """Get all available labels"""
    return jsonify({
        'labels': list(label_map.values()),
        'count': len(label_map)
    }), 200

if __name__ == '__main__':
    # Initialize Triton connection
    initialize_triton_client()
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
