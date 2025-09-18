import kagglehub
import os
import glob
import shutil
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
            
            # Deterministic local cache path for this dataset
            safe_name = dataset_name.replace('/', '__')
            local_dataset_dir = os.path.join(self.download_dir, safe_name)
            os.makedirs(local_dataset_dir, exist_ok=True)

            # If already cached with CSVs, skip fresh download
            existing_csvs = self.get_csv_files_from_dataset(local_dataset_dir)
            if existing_csvs:
                logger.info(f"Using cached dataset at {local_dataset_dir} ({len(existing_csvs)} CSVs)")
                files = []
                for root, _, filenames in os.walk(local_dataset_dir):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        file_size = os.path.getsize(file_path)
                        files.append({
                            "name": filename,
                            "path": file_path,
                            "size_mb": round(file_size / (1024 * 1024), 2),
                            "relative_path": os.path.relpath(file_path, local_dataset_dir)
                        })
                csv_files = [f for f in files if f["name"].lower().endswith('.csv')]
                return {
                    "dataset_name": dataset_name,
                    "download_path": local_dataset_dir,
                    "total_files": len(files),
                    "csv_files": len(csv_files),
                    "files": files,
                    "csv_file_paths": [f["path"] for f in csv_files],
                    "status": "success"
                }

            # Otherwise, download and copy into cache directory
            path = kagglehub.dataset_download(dataset_name)

            # Copy all files from KaggleHub temp path to our cache folder
            for root, _, filenames in os.walk(path):
                for filename in filenames:
                    src_path = os.path.join(root, filename)
                    rel = os.path.relpath(src_path, path)
                    dst_path = os.path.join(local_dataset_dir, rel)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)

            # Scan cached directory
            files = []
            for root, _, filenames in os.walk(local_dataset_dir):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    file_size = os.path.getsize(file_path)
                    files.append({
                        "name": filename,
                        "path": file_path,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "relative_path": os.path.relpath(file_path, local_dataset_dir)
                    })
            csv_files = [f for f in files if f["name"].lower().endswith('.csv')]

            result = {
                "dataset_name": dataset_name,
                "download_path": local_dataset_dir,
                "total_files": len(files),
                "csv_files": len(csv_files),
                "files": files,
                "csv_file_paths": [f["path"] for f in csv_files],
                "status": "success"
            }

            logger.info(f"Cached {len(files)} files ({len(csv_files)} CSV) to {local_dataset_dir}")
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
