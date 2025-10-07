#!/usr/bin/env python3
"""
Data Preprocessing Script for XPS 15
Optimized for multi-core CPU processing
"""

import pandas as pd
import numpy as np
import multiprocessing as mp
from pathlib import Path
import logging
import argparse
from typing import Dict, List
from datasets import load_dataset, Dataset, DatasetDict
from transformers import AutoTokenizer
import json
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataPreprocessor:
    """Multi-core data preprocessing pipeline"""
    
    def __init__(self, num_workers: int = None):
        self.num_workers = num_workers or mp.cpu_count()
        self.tokenizer = None
        logger.info(f"Initialized with {self.num_workers} workers")
    
    def load_raw_data(self, data_path: str) -> pd.DataFrame:
        """Load data from various formats"""
        logger.info(f"Loading data from {data_path}")
        
        path = Path(data_path)
        if path.suffix == '.parquet':
            df = pd.read_parquet(path)
        elif path.suffix == '.csv':
            df = pd.read_csv(path)
        elif path.suffix == '.jsonl':
            df = pd.read_json(path, lines=True)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")
        
        logger.info(f"Loaded {len(df)} rows")
        return df
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not isinstance(text, str):
            return ""
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Basic cleaning
        text = text.strip()
        
        return text
    
    def tokenize_function(self, examples: Dict) -> Dict:
        """Tokenization function for dataset.map()"""
        if self.tokenizer is None:
            raise ValueError("Tokenizer not initialized")
        
        return self.tokenizer(
            examples['text'],
            truncation=True,
            padding='max_length',
            max_length=512,
            return_tensors=None
        )
    
    def preprocess_for_training(
        self,
        input_path: str,
        output_path: str,
        model_name: str = 'bert-base-uncased',
        test_size: float = 0.1
    ):
        """
        Complete preprocessing pipeline for model training
        
        Args:
            input_path: Path to raw data
            output_path: Path to save processed data
            model_name: Tokenizer model name
            test_size: Validation split ratio
        """
        logger.info("Starting preprocessing pipeline")
        
        # Load data
        df = self.load_raw_data(input_path)
        
        # Clean text
        logger.info("Cleaning text...")
        df['text'] = df['text'].apply(self.clean_text)
        
        # Remove empty rows
        df = df[df['text'].str.len() > 0]
        logger.info(f"Retained {len(df)} rows after cleaning")
        
        # Convert to HuggingFace Dataset
        dataset = Dataset.from_pandas(df)
        
        # Split train/val
        dataset = dataset.train_test_split(test_size=test_size, seed=42)
        
        # Initialize tokenizer
        logger.info(f"Loading tokenizer: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Tokenize
        logger.info("Tokenizing...")
        tokenized_dataset = dataset.map(
            self.tokenize_function,
            batched=True,
            num_proc=self.num_workers,
            remove_columns=dataset['train'].column_names,
            desc="Tokenizing"
        )
        
        # Save
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving to {output_dir}")
        tokenized_dataset.save_to_disk(str(output_dir))
        
        # Save metadata
        metadata = {
            'num_train_samples': len(tokenized_dataset['train']),
            'num_val_samples': len(tokenized_dataset['test']),
            'tokenizer': model_name,
            'max_length': 512,
            'original_columns': df.columns.tolist()
        }
        
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("Preprocessing complete!")
        
        # Send webhook notification
        self.notify_completion(metadata)
        
        return metadata
    
    def preprocess_for_inference(
        self,
        input_path: str,
        output_path: str,
        batch_size: int = 1000
    ):
        """
        Preprocess data for batch inference
        
        Args:
            input_path: Path to raw data
            output_path: Path to save processed batches
            batch_size: Samples per batch file
        """
        logger.info("Preprocessing for inference")
        
        df = self.load_raw_data(input_path)
        df['text'] = df['text'].apply(self.clean_text)
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save in batches
        num_batches = len(df) // batch_size + 1
        
        for i in range(num_batches):
            start = i * batch_size
            end = min((i + 1) * batch_size, len(df))
            
            batch_df = df.iloc[start:end]
            batch_file = output_dir / f'batch_{i:04d}.parquet'
            
            batch_df.to_parquet(batch_file, index=False)
            logger.info(f"Saved batch {i+1}/{num_batches}: {len(batch_df)} samples")
        
        metadata = {
            'num_batches': num_batches,
            'batch_size': batch_size,
            'total_samples': len(df)
        }
        
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    def extract_obsidian_dataset(
        self,
        vault_path: str,
        output_path: str
    ):
        """
        Extract training data from Obsidian vault
        
        Args:
            vault_path: Path to Obsidian vault
            output_path: Path to save extracted dataset
        """
        logger.info(f"Extracting from Obsidian vault: {vault_path}")
        
        import yaml
        
        vault = Path(vault_path)
        dataset = []
        
        for md_file in vault.rglob('*.md'):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse frontmatter
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        body = parts[2].strip()
                        
                        # Extract labels
                        tags = frontmatter.get('tags', [])
                        if isinstance(tags, str):
                            tags = [tags]
                        
                        kind = frontmatter.get('kind', 'unknown')
                        para_folder = md_file.parent.name
                        
                        # Combine labels
                        labels = tags + [f"kind:{kind}", f"para:{para_folder}"]
                        
                        dataset.append({
                            'text': body[:512],  # Limit for BERT
                            'labels': labels,
                            'file': str(md_file.relative_to(vault))
                        })
            
            except Exception as e:
                logger.warning(f"Failed to process {md_file}: {e}")
        
        # Convert to DataFrame
        df = pd.DataFrame(dataset)
        
        # Multi-hot encode labels
        from sklearn.preprocessing import MultiLabelBinarizer
        mlb = MultiLabelBinarizer()
        label_matrix = mlb.fit_transform(df['labels'])
        
        # Create label columns
        for i, label in enumerate(mlb.classes_):
            df[f'label_{label}'] = label_matrix[:, i]
        
        # Save
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        df.to_parquet(output_dir / 'obsidian_dataset.parquet', index=False)
        
        # Save label mapping
        with open(output_dir / 'labels.txt', 'w') as f:
            for label in mlb.classes_:
                f.write(f"{label}\n")
        
        metadata = {
            'num_samples': len(df),
            'num_labels': len(mlb.classes_),
            'labels': list(mlb.classes_)
        }
        
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Extracted {len(df)} samples with {len(mlb.classes_)} unique labels")
        
        return metadata
    
    def notify_completion(self, metadata: Dict):
        """Send webhook notification to n8n"""
        try:
            webhook_url = "http://n8n_automation:5678/webhook/data-ready"
            response = requests.post(
                webhook_url,
                json={
                    'event': 'preprocessing_complete',
                    'metadata': metadata
                },
                timeout=5
            )
            logger.info(f"Webhook notification sent: {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to send webhook: {e}")

def main():
    parser = argparse.ArgumentParser(description='Data Preprocessing Pipeline')
    parser.add_argument('--mode', choices=['training', 'inference', 'obsidian'],
                       required=True, help='Preprocessing mode')
    parser.add_argument('--input', required=True, help='Input data path')
    parser.add_argument('--output', required=True, help='Output path')
    parser.add_argument('--workers', type=int, help='Number of workers')
    parser.add_argument('--model', default='bert-base-uncased',
                       help='Tokenizer model name')
    
    args = parser.parse_args()
    
    preprocessor = DataPreprocessor(num_workers=args.workers)
    
    if args.mode == 'training':
        preprocessor.preprocess_for_training(
            args.input,
            args.output,
            args.model
        )
    elif args.mode == 'inference':
        preprocessor.preprocess_for_inference(
            args.input,
            args.output
        )
    elif args.mode == 'obsidian':
        preprocessor.extract_obsidian_dataset(
            args.input,
            args.output
        )

if __name__ == '__main__':
    main()
