# Hospital Chatbot System

A comprehensive hospital chatbot system that enables patients to book appointments, receive medical guidance, and manage healthcare via conversation.

## Features

- Patient registration and validation
- Symptom-based doctor assignment using LLM
- Appointment booking with slot selection
- Email confirmations and 24-hour reminders
- Follow-up scheduling and feedback collection
- Integrated with real patient/doctor data

## Prerequisites

- Python 3.8 or higher
- Django 5.2.6 or higher
- SQLite (included with Python)
- Groq API key for LLM functionality

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd HospitalChatbot
   ```

2. Navigate to the project directory:
   ```bash
   cd HospitalChatbot
   ```

3. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

4. Install Django:
   ```bash
   pip install django
   ```

5. Create a `.env` file in the `HospitalChatbot/HospitalChatbot/` directory by copying the `.env.example` file and adding your credentials:
   ```bash
   cp .env.example .env
   # On Windows:
   # copy .env.example .env
   ```
   Then edit the `.env` file to add your actual credentials.

6. Set up the database:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. Create a superuser (optional):
   ```bash
   python manage.py createsuperuser
   ```

8. Run the development server:
   ```bash
   python manage.py runserver
   ```

9. Access the application at `http://127.0.0.1:8000`

## Usage

1. Open your web browser and navigate to `http://127.0.0.1:8000`
2. Click on the chat icon (bottom-right corner) to open the chatbot
3. Follow the prompts to:
   - Register as a new patient or log in as an existing patient
   - Describe your health problem
   - Get assigned to an appropriate doctor based on your symptoms
   - Select an available appointment slot
   - Receive email confirmation of your appointment

## Project Structure

```
HospitalChatbot/
├── HospitalChatbot/           # Django project settings
│   ├── app1/                 # Main application
│   │   ├── models.py         # Database models
│   │   ├── views.py          # API endpoints
│   │   ├── llm.py            # LLM integration
│   │   ├── templates/        # HTML templates
│   │   └── static/           # Static files (images, CSS, JS)
│   ├── .env.example          # Example environment file (copy to .env)
│   └── manage.py             # Django management script
├── .env.example              # Example environment file (copy to .env)
└── README.md                 # This file
```

## Configuration

### Email Setup

To enable email functionality, edit your `.env` file with your email credentials:

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com
```

Note: For Gmail, you'll need to use an App Password instead of your regular password.

### Database

The system uses SQLite by default. The database file is `db.sqlite3` and is automatically created when you run migrations.

## Troubleshooting

1. **Chatbot not responding**: Ensure the Django development server is running
2. **Email not sending**: Check your email configuration in the `.env` file
3. **Doctor assignment not working**: Verify your Groq API key is correct
4. **Static files not loading**: Run `python manage.py collectstatic`


## Acknowledgments

- Powered by Django Framework
- Doctor assignment powered by Groq LLM API
- Uses SQLite for data storage
