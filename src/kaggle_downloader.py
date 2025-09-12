import kagglehub
import os
import glob
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KaggleDownloader:
    def __init__(self, download_dir: str = "./datasets"):
        """Initialize Kaggle downloader with a download directory"""
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
    
    def download_dataset(self, dataset_name: str) -> Dict[str, str]:
        """
        Download a Kaggle dataset and return information about downloaded files
        
        Args:
            dataset_name: Kaggle dataset name (e.g., "yashdevladdha/uber-ride-analytics-dashboard")
            
        Returns:
            Dictionary with download information
        """
        try:
            logger.info(f"Downloading dataset: {dataset_name}")
            
            # Download the dataset
            path = kagglehub.dataset_download(dataset_name)
            
            # Find all files in the downloaded directory
            files = []
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    file_size = os.path.getsize(file_path)
                    files.append({
                        "name": filename,
                        "path": file_path,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "relative_path": os.path.relpath(file_path, path)
                    })
            
            # Find CSV files specifically
            csv_files = [f for f in files if f["name"].lower().endswith('.csv')]
            
            result = {
                "dataset_name": dataset_name,
                "download_path": path,
                "total_files": len(files),
                "csv_files": len(csv_files),
                "files": files,
                "csv_file_paths": [f["path"] for f in csv_files],
                "status": "success"
            }
            
            logger.info(f"Successfully downloaded {len(files)} files, {len(csv_files)} CSV files")
            return result
            
        except Exception as e:
            logger.error(f"Error downloading dataset {dataset_name}: {e}")
            return {
                "dataset_name": dataset_name,
                "status": "error",
                "error": str(e)
            }
    
    def list_downloaded_datasets(self) -> List[Dict[str, str]]:
        """List all downloaded datasets in the download directory"""
        try:
            datasets = []
            if os.path.exists(self.download_dir):
                for item in os.listdir(self.download_dir):
                    item_path = os.path.join(self.download_dir, item)
                    if os.path.isdir(item_path):
                        # Count files in the dataset directory
                        files = []
                        for root, dirs, filenames in os.walk(item_path):
                            for filename in filenames:
                                files.append(filename)
                        
                        datasets.append({
                            "name": item,
                            "path": item_path,
                            "file_count": len(files),
                            "files": files[:10]  # Show first 10 files
                        })
            
            return datasets
            
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            return []
    
    def get_csv_files_from_dataset(self, dataset_path: str) -> List[str]:
        """Get all CSV files from a downloaded dataset"""
        try:
            csv_files = []
            for root, dirs, filenames in os.walk(dataset_path):
                for filename in filenames:
                    if filename.lower().endswith('.csv'):
                        csv_files.append(os.path.join(root, filename))
            
            return csv_files
            
        except Exception as e:
            logger.error(f"Error finding CSV files: {e}")
            return []
