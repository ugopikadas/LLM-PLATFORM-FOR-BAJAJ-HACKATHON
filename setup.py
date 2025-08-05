"""
Setup script for the LLM Document Processing System
"""

import os
import sys
import subprocess
from pathlib import Path


def install_dependencies():
    """Install required Python packages"""
    print("Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Python dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error installing dependencies: {e}")
        return False
    return True


def download_spacy_model():
    """Download spaCy English model"""
    print("Downloading spaCy English model...")
    try:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        print("✓ spaCy model downloaded successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error downloading spaCy model: {e}")
        print("You can manually install it later with: python -m spacy download en_core_web_sm")
        return False
    return True


def create_env_file():
    """Create .env file from template"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            print("Creating .env file from template...")
            with open('.env.example', 'r') as src, open('.env', 'w') as dst:
                dst.write(src.read())
            print("✓ .env file created")
            print("⚠️  Please edit .env file and add your OpenAI API key")
        else:
            print("✗ .env.example not found")
            return False
    else:
        print("✓ .env file already exists")
    return True


def create_directories():
    """Create necessary directories"""
    directories = [
        "vector_db",
        "logs",
        "data/uploads"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    return True


def setup_sample_data():
    """Load sample documents into the system"""
    print("Setting up sample data...")
    try:
        # Import here to avoid import errors during setup
        sys.path.append('src')
        from src.services.document_processor import DocumentProcessor
        from src.services.vector_store import VectorStore
        
        processor = DocumentProcessor()
        vector_store = VectorStore()
        
        sample_files = [
            "data/sample_policies/health_insurance_policy.txt",
            "data/sample_policies/corporate_policy.txt"
        ]
        
        for file_path in sample_files:
            if os.path.exists(file_path):
                print(f"Processing {file_path}...")
                chunks = processor.process_document(file_path)
                vector_store.add_documents(chunks)
                print(f"✓ Added {len(chunks)} chunks from {file_path}")
            else:
                print(f"⚠️  Sample file not found: {file_path}")
        
        print("✓ Sample data setup completed")
        return True
        
    except Exception as e:
        print(f"✗ Error setting up sample data: {e}")
        print("You can manually upload documents later through the web interface")
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up LLM Document Processing System...")
    print("=" * 50)
    
    success = True
    
    # Step 1: Install dependencies
    if not install_dependencies():
        success = False
    
    # Step 2: Download spaCy model
    if not download_spacy_model():
        success = False
    
    # Step 3: Create .env file
    if not create_env_file():
        success = False
    
    # Step 4: Create directories
    if not create_directories():
        success = False
    
    # Step 5: Setup sample data (only if API key is available)
    if os.getenv('OPENAI_API_KEY'):
        if not setup_sample_data():
            success = False
    else:
        print("⚠️  OPENAI_API_KEY not found, skipping sample data setup")
        print("   Add your API key to .env file and run: python -c 'from setup import setup_sample_data; setup_sample_data()'")
    
    print("=" * 50)
    if success:
        print("✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit .env file and add your OpenAI API key")
        print("2. Run the application: python main.py")
        print("3. Open http://localhost:8000 in your browser")
    else:
        print("⚠️  Setup completed with some warnings")
        print("Please check the messages above and resolve any issues")


if __name__ == "__main__":
    main()
