 Hotel Management Backend

A comprehensive backend system for hotel management, built with FastAPI, SQLModel, and modern Python practices. The system features guest registration, room management, booking, invoicing, DigiLocker integration, OCR processing, and ML-based occupancy prediction.

 Features

 Core Functionality
- Guest Management: Store and manage guest information with comprehensive profiles
- Room Management: Track room availability, types, pricing, and maintenance status
- Booking System: Handle reservations, check-ins, check-outs with complete workflow
- Invoicing: Detailed invoice generation with line items, taxes, and discounts
- User Management: Role-based access control with JWT authentication
- Email Notifications: Automated emails for bookings, invoices, and system alerts

 Advanced Features
- DigiLocker Integration: OAuth-based secure access to guest documents
- OCR Processing: Extract information from ID documents using Tesseract
- Machine Learning: Occupancy prediction using RandomForestRegressor
- Background Tasks: Asynchronous processing for long-running operations
- System Backup/Restore: Automated backup and restore functionality
- CSV Import/Export: Data migration support for legacy systems
- Comprehensive Logging: Structured logging with request tracking
- API Security: Rate limiting, CORS, and JWT authentication
- Error Handling: Standardized error responses and validation

 Technical Implementation

 API Framework
- FastAPI: Modern, fast web framework for building APIs with automatic OpenAPI documentation
- SQLModel: SQL databases in Python, designed for simplicity, compatibility, and robustness
- Pydantic: Data validation and settings management using Python type annotations
- JWT Authentication: Secure, token-based authentication with role-based access control

 Machine Learning
- Scikit-learn: Occupancy prediction using RandomForestRegressor
- Automated Training: Background tasks for model training and evaluation
- Feature Engineering: Data preprocessing and feature extraction
- Historical Data: Collection and analysis of occupancy patterns

 OCR Processing
- Tesseract OCR: Document processing with high accuracy
- Image Preprocessing: Enhancement techniques for better OCR results
- Structured Extraction: Pattern matching for specific document fields
- Background Processing: Asynchronous OCR task execution

 Security & Performance
- Middleware Stack: Comprehensive middleware for security and performance
- Request Tracking: Unique ID for each request for debugging and auditing
- Rate Limiting: Protection against abuse and DoS attacks
- CORS Configuration: Secure cross-origin resource sharing
- Error Standardization: Consistent error responses across the API

 Getting Started

 Prerequisites
- Python 3.9+
- Tesseract OCR installed on the system
- SMTP server for email functionality (optional)

 Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file based on `.env.example` with your configuration

 Running the Application

1. Start the development server:
   ```bash
    Using the provided scripts
   ./start_server.sh   On Windows: start_server.bat
   
    Or directly with uvicorn
   uvicorn app.main:app --reload
   ```

2. Access the API documentation:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

 Project Structure

```
hotel_management_backend/
├── app/
│   ├── api/               API endpoints
│   ├── auth/              Authentication logic
│   ├── db/                Database setup
│   ├── middleware/        Middleware components
│   ├── models/            Database models
│   ├── schemas/           Pydantic schemas
│   ├── services/          Business logic
│   ├── utils/             Utility functions
│   ├── config.py          Application config
│   └── main.py            FastAPI app setup
├── uploads/               Uploaded files
├── ml_models/             ML model files
└── requirements.txt       Dependencies
```

 API Documentation

The API is self-documented using OpenAPI. After starting the server, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

 Development



 
 License

This project is licensed under the MIT License.