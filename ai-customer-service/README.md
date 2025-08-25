# AI Customer Service Assistant

A comprehensive AI-powered customer service system built with FastAPI, React, and OpenAI integration.

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-customer-service

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend setup (in another terminal)
cd frontend
npm install
npm start
```

## 📁 Project Structure

```
ai-customer-service/
├── backend/                 # FastAPI backend
│   ├── app/                 # Application code
│   ├── tests/               # Backend tests
│   ├── main.py              # Entry point
│   └── requirements.txt     # Python dependencies
├── frontend/                # React frontend
│   ├── src/                 # Source code
│   ├── public/              # Static assets
│   └── package.json         # Node dependencies
├── .github/workflows/       # CI/CD pipelines
├── docker-compose.yml       # Docker orchestration
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

Create `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_customer_service
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
REDIS_URL=redis://localhost:6379
```

## 🧪 Testing

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Frontend tests
cd frontend
npm test

# Run workflow validation
./validate-workflow.sh
```

## 📚 Documentation

- [API Documentation](API.md) - Complete API reference
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `./validate-workflow.sh`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Check the [DEPLOYMENT.md](DEPLOYMENT.md) for common troubleshooting
- Review the API documentation in [API.md](API.md)
- Run `./validate-workflow.sh` to check for configuration issues
