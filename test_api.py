#!/usr/bin/env python3
"""
Test script for the Intelligent Document Understanding API
"""

import requests
import json
import time
from pathlib import Path

# API Configuration
API_BASE_URL = "http://localhost:8000"
API_ENDPOINTS = {
    "health": f"{API_BASE_URL}/health",
    "upload": f"{API_BASE_URL}/api/v1/upload",
    "classify": f"{API_BASE_URL}/api/v1/classify",
    "extract": f"{API_BASE_URL}/api/v1/extract",
    "types": f"{API_BASE_URL}/api/v1/types",
    "stats": f"{API_BASE_URL}/api/v1/stats"
}

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing Health Check...")
    try:
        response = requests.get(API_ENDPOINTS["health"])
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Status: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")

def test_get_document_types():
    """Test getting supported document types"""
    print("\n📋 Testing Document Types...")
    try:
        response = requests.get(API_ENDPOINTS["types"])
        if response.status_code == 200:
            data = response.json()
            print("✅ Document types retrieved")
            print(f"   Supported types: {data['supported_types']}")
            print(f"   Fields per type: {json.dumps(data['document_types'], indent=2)}")
        else:
            print(f"❌ Failed to get document types: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting document types: {str(e)}")

def test_classify_text():
    """Test document classification with sample text"""
    print("\n🏷️  Testing Document Classification...")
    
    sample_texts = [
        {
            "text": "INVOICE\nInvoice #: INV-2024-001\nDate: 2024-01-15\nDue Date: 2024-02-15\nTotal Amount: $1,250.00\nVendor: ABC Company\nCustomer: XYZ Corp",
            "expected_type": "invoice"
        },
        {
            "text": "RECEIPT\nStore: Walmart\nDate: 2024-01-20\nItems: Groceries, Electronics\nTotal: $89.99\nPayment Method: Credit Card",
            "expected_type": "receipt"
        },
        {
            "text": "CONTRACT AGREEMENT\nContract #: CON-2024-001\nParties: Company A and Company B\nStart Date: 2024-01-01\nEnd Date: 2024-12-31\nContract Value: $50,000",
            "expected_type": "contract"
        }
    ]
    
    for i, sample in enumerate(sample_texts, 1):
        print(f"   Testing sample {i}...")
        try:
            response = requests.post(
                API_ENDPOINTS["classify"],
                data={"text": sample["text"]}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Classified as: {result['document_type']} (confidence: {result['confidence']:.2f})")
                if result['document_type'] == sample['expected_type']:
                    print(f"   ✅ Expected type matched!")
                else:
                    print(f"   ⚠️  Expected: {sample['expected_type']}, Got: {result['document_type']}")
            else:
                print(f"   ❌ Classification failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Classification error: {str(e)}")

def test_entity_extraction():
    """Test entity extraction with sample text"""
    print("\n🔍 Testing Entity Extraction...")
    
    sample_data = {
        "text": "INVOICE\nInvoice #: INV-2024-001\nDate: 2024-01-15\nDue Date: 2024-02-15\nTotal Amount: $1,250.00\nVendor Name: ABC Company\nVendor Address: 123 Main St, City, State\nCustomer Name: XYZ Corp\nCustomer Address: 456 Business Ave, City, State",
        "document_type": "invoice"
    }
    
    try:
        response = requests.post(
            API_ENDPOINTS["extract"],
            json=sample_data
        )
        if response.status_code == 200:
            result = response.json()
            print("✅ Entity extraction successful")
            print(f"   Extracted entities: {json.dumps(result['entities'], indent=2)}")
            if result.get('confidence_scores'):
                print(f"   Confidence scores: {json.dumps(result['confidence_scores'], indent=2)}")
        else:
            print(f"❌ Entity extraction failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Entity extraction error: {str(e)}")

def test_file_upload():
    """Test file upload (if sample files are available)"""
    print("\n📁 Testing File Upload...")
    
    # Look for sample files in the archive directory
    sample_files = []
    archive_dir = Path("archive/docs-sm")
    
    if archive_dir.exists():
        # Look for sample files in subdirectories
        for subdir in archive_dir.iterdir():
            if subdir.is_dir():
                for file_path in subdir.glob("*.jpg"):
                    sample_files.append((file_path, subdir.name))
                    if len(sample_files) >= 2:  # Test with 2 files
                        break
            if len(sample_files) >= 2:
                break
    
    if not sample_files:
        print("   ⚠️  No sample files found in archive/docs-sm directory")
        print("   💡 You can add sample images/PDFs to test file upload")
        return
    
    for file_path, doc_type in sample_files:
        print(f"   Testing upload of {file_path.name} (expected type: {doc_type})...")
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'image/jpeg')}
                response = requests.post(API_ENDPOINTS["upload"], files=files)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Upload successful")
                print(f"   📄 Detected type: {result['document_type']} (confidence: {result['confidence']:.2f})")
                print(f"   ⏱️  Processing time: {result['processing_time']}")
                print(f"   🔍 Extracted entities: {len(result['entities'])} fields")
                
                # Show some extracted entities
                for field, value in list(result['entities'].items())[:3]:
                    if value:
                        print(f"      {field}: {value}")
            else:
                print(f"   ❌ Upload failed: {response.status_code}")
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Upload error: {str(e)}")

def test_statistics():
    """Test getting processing statistics"""
    print("\n📊 Testing Statistics...")
    try:
        response = requests.get(API_ENDPOINTS["stats"])
        if response.status_code == 200:
            data = response.json()
            print("✅ Statistics retrieved")
            print(f"   Total documents: {data.get('total_documents', 0)}")
            print(f"   Document type distribution: {json.dumps(data.get('document_types', {}), indent=2)}")
        else:
            print(f"❌ Failed to get statistics: {response.status_code}")
    except Exception as e:
        print(f"❌ Statistics error: {str(e)}")

def main():
    """Run all tests"""
    print("🚀 Starting Intelligent Document Understanding API Tests")
    print("=" * 60)
    
    # Wait a moment for API to be ready
    print("⏳ Waiting for API to be ready...")
    time.sleep(2)
    
    # Run tests
    test_health_check()
    test_get_document_types()
    test_classify_text()
    test_entity_extraction()
    test_file_upload()
    test_statistics()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("\n📖 Next steps:")
    print("   1. Check the API documentation at: http://localhost:8000/docs")
    print("   2. Try uploading your own documents")
    print("   3. Explore the UI at: http://localhost:8501")

if __name__ == "__main__":
    main() 