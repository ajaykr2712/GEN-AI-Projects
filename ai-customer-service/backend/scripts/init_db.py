import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import engine, SessionLocal, Base
from app.models.models import User, FAQ, KnowledgeBase
from app.services.auth_service import auth_service

# Sample data
SAMPLE_FAQS = [
    {
        "question": "How do I reset my password?",
        "answer": "To reset your password, click on 'Forgot Password' on the login page and follow the instructions sent to your email.",
        "category": "account",
        "tags": "password,reset,account"
    },
    {
        "question": "How can I contact customer support?",
        "answer": "You can contact our customer support team through this chat interface, email at support@company.com, or call us at 1-800-SUPPORT.",
        "category": "general",
        "tags": "contact,support,help"
    },
    {
        "question": "What are your business hours?",
        "answer": "Our customer support is available 24/7 through this AI assistant. Live agents are available Monday-Friday 9AM-6PM EST.",
        "category": "general",
        "tags": "hours,availability,support"
    },
    {
        "question": "How do I update my billing information?",
        "answer": "To update your billing information, go to Account Settings > Billing and click 'Update Payment Method'.",
        "category": "billing",
        "tags": "billing,payment,update"
    },
    {
        "question": "Why is my account suspended?",
        "answer": "Accounts may be suspended for various reasons including payment issues or policy violations. Please contact support for specific details about your account.",
        "category": "account",
        "tags": "suspended,account,violation"
    }
]

SAMPLE_KNOWLEDGE_BASE = [
    {
        "title": "Getting Started Guide",
        "content": "Welcome to our AI Customer Service platform! This guide will help you get started with using our services. First, create an account and verify your email. Then, explore the chat interface to interact with our AI assistant.",
        "category": "tutorial",
        "tags": "getting started,tutorial,guide"
    },
    {
        "title": "Troubleshooting Common Issues",
        "content": "Common issues and solutions: 1) Login problems - clear browser cache, 2) Slow performance - check internet connection, 3) Missing features - ensure you're using the latest version.",
        "category": "troubleshooting",
        "tags": "troubleshooting,issues,solutions"
    },
    {
        "title": "Privacy and Security",
        "content": "We take your privacy seriously. All conversations are encrypted, personal data is protected according to GDPR standards, and we never share your information with third parties without consent.",
        "category": "privacy",
        "tags": "privacy,security,data protection"
    },
    {
        "title": "AI Assistant Capabilities",
        "content": "Our AI assistant can help with: answering questions, troubleshooting issues, processing support requests, providing product information, and escalating complex issues to human agents when needed.",
        "category": "features",
        "tags": "AI,capabilities,features"
    }
]

def init_database():
    """Initialize database with sample data."""
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if admin user exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            # Create admin user
            admin_user = User(
                username="admin",
                email="admin@example.com",
                full_name="System Administrator",
                hashed_password=auth_service.get_password_hash("admin123"),
                is_admin=True
            )
            db.add(admin_user)
            print("Created admin user: admin/admin123")
        
        # Create demo user
        demo_user = db.query(User).filter(User.username == "demo").first()
        if not demo_user:
            demo_user = User(
                username="demo",
                email="demo@example.com",
                full_name="Demo User",
                hashed_password=auth_service.get_password_hash("demo123"),
                is_admin=False
            )
            db.add(demo_user)
            print("Created demo user: demo/demo123")
        
        # Add sample FAQs
        existing_faqs = db.query(FAQ).count()
        if existing_faqs == 0:
            for faq_data in SAMPLE_FAQS:
                faq = FAQ(**faq_data)
                db.add(faq)
            print(f"Added {len(SAMPLE_FAQS)} sample FAQs")
        
        # Add sample knowledge base entries
        existing_kb = db.query(KnowledgeBase).count()
        if existing_kb == 0:
            for kb_data in SAMPLE_KNOWLEDGE_BASE:
                kb_entry = KnowledgeBase(**kb_data)
                db.add(kb_entry)
            print(f"Added {len(SAMPLE_KNOWLEDGE_BASE)} knowledge base entries")
        
        db.commit()
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
