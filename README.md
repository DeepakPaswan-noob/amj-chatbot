# AMJC Student Assistant Chatbot

An intelligent chatbot designed specifically for students of Agurchand Manmull Jain College (AMJC) to help with college-related queries, course information, and campus services.

## Features

### 🤖 **Intelligent Response System**
- Natural Language Processing using NLTK
- Smart query matching with AMJC-specific FAQ database
- Context-aware responses for college queries

### 💬 **Modern Chat Interface**
- Clean, responsive design with AMJC branding
- Real-time typing indicators
- Smooth animations and transitions
- Mobile-friendly interface

### 📚 **AMJC Knowledge Base**
- Course information across all three schools (Commerce, Science, Arts)
- Admission process and application details
- Contact information for both shifts
- College facilities and infrastructure details
- Placement opportunities and alumni achievements
- Department-wise program information

### 💾 **Data Storage**
- SQLite database for conversation history
- AMJC-specific FAQ management system
- Conversation analytics

## Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: SQLite
- **NLP**: NLTK (Natural Language Toolkit)
- **Styling**: Modern CSS with gradients and animations

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Setup Steps

1. **Clone or download the project files**

2. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

## Project Structure

```
STUDENT-CHATBOT/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── chatbot.db            # SQLite database (auto-created)
├── templates/
│   └── index.html        # Main chat interface
└── static/
    ├── css/
    │   └── style.css     # Styling and animations
    └── js/
        └── script.js     # Frontend functionality
```

## How It Works

### 1. **Natural Language Processing**
The chatbot uses NLTK to:
- Tokenize user input
- Remove stop words
- Lemmatize words for better matching
- Score similarity between queries and FAQ entries

### 2. **Knowledge Base Matching**
- Preprocesses both user queries and FAQ content
- Uses word overlap scoring to find best matches
- Falls back to general help when no specific match is found

### 3. **Conversation Storage**
- All conversations are stored in SQLite database
- Enables analytics and improvement of responses
- Maintains conversation history

## Customization

### Adding New FAQs
You can add new FAQs by modifying the `default_faqs` list in `app.py`:

```python
{
    "question": "Your question here?",
    "answer": "Your detailed answer here.",
    "category": "category_name",
    "keywords": "relevant keywords for matching"
}
```

### Styling Customization
Modify `static/css/style.css` to change:
- Color schemes
- Layout and spacing
- Animations and effects
- Responsive behavior

### Adding New Features
The modular structure allows easy addition of:
- New API endpoints in `app.py`
- Frontend features in `script.js`
- Database schema changes
- Integration with external APIs

## API Endpoints

### `POST /chat`
Send a message to the chatbot
```json
{
    "message": "How do I register for classes?"
}
```

**Response:**
```json
{
    "response": "You can register for classes through...",
    "timestamp": "2024-01-15T10:30:00"
}
```

### `GET /health`
Check if the service is running
```json
{
    "status": "healthy"
}
```

## Common AMJC Queries Supported

- **About AMJC**: College history, accreditation, affiliation with University of Madras
- **Admissions**: Application process, course offerings, eligibility criteria
- **Courses**: UG/PG/PhD programs across Commerce, Science, and Arts schools
- **Contact**: Phone numbers, email addresses, location details for both shifts
- **Facilities**: Campus infrastructure, libraries, labs, student services
- **Placements**: Career opportunities, industry partnerships, notable alumni
- **Departments**: Information about all departments and their specializations

## Troubleshooting

### Common Issues

1. **NLTK Data Not Found**
   - The app automatically downloads required NLTK data
   - If issues persist, manually run: `python -c "import nltk; nltk.download('all')"`

2. **Port Already in Use**
   - Change the port in `app.py`: `app.run(debug=True, port=5001)`

3. **Database Issues**
   - Delete `chatbot.db` to reset the database
   - The app will recreate it with default data

## Future Enhancements

- **Advanced NLP**: Integration with spaCy or transformers
- **Voice Interface**: Speech-to-text and text-to-speech
- **Multi-language Support**: Internationalization
- **Analytics Dashboard**: Conversation insights and metrics
- **Integration**: Connect with student information systems
- **Mobile App**: Native mobile applications

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For support or questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation for common solutions

---

**Happy Learning! 🎓**
