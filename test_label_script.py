import os
import sys

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.agents.resolution.core.services.return_label_service import generate_return_label

def test_label():
    print("Testing label generation...")
    try:
        url = generate_return_label(
            order_id="TEST-12345",
            product="Premium Wireless Headphones",
            size=1,
            message="Please process the refund as requested."
        )
        print(f"Success! Label generated: {url}")
        
        # Check if file exists
        base_dir = os.path.dirname(os.path.abspath(__file__))
        label_path = os.path.join(base_dir, "backend/app/agents/resolution/static/labels", url)
        if os.path.exists(label_path):
            print(f"File verified at: {label_path}")
        else:
            print(f"Warning: File not found at {label_path}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_label()
