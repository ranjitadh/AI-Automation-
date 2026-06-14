#!/bin/bash
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Seeding default plans..."
python manage.py shell -c "
from apps.billing.models import Plan
if not Plan.objects.exists():
    Plan.objects.create(name='Free', price_monthly=0, price_yearly=0, max_applications=50, max_active_campaigns=3, max_users=1, has_analytics=False, has_automation=False, sort_order=1)
    Plan.objects.create(name='Pro', price_monthly=29, price_yearly=290, max_applications=500, max_active_campaigns=10, max_users=5, has_analytics=True, has_automation=True, sort_order=2)
    Plan.objects.create(name='Business', price_monthly=99, price_yearly=990, max_applications=5000, max_active_campaigns=50, max_users=25, has_analytics=True, has_automation=True, sort_order=3)
    print('Default plans seeded.')
else:
    print('Plans already exist, skipping.')
"

echo "Seeding system questions..."
python manage.py shell -c "
from apps.questions.models import QuestionBank
if not QuestionBank.objects.exists():
    questions = [
        {'category': 'motivation', 'question': 'Why do you want to work here?'},
        {'category': 'experience', 'question': 'Describe your relevant experience for this role.'},
        {'category': 'skills', 'question': 'What are your strongest technical skills?'},
        {'category': 'goals', 'question': 'Where do you see yourself in 5 years?'},
        {'category': 'teamwork', 'question': 'Describe a time you worked in a team.'},
        {'category': 'conflict', 'question': 'How do you handle conflict at work?'},
        {'category': 'leadership', 'question': 'Describe a leadership experience.'},
        {'category': 'failure', 'question': 'Tell me about a time you failed and what you learned.'},
        {'category': 'achievement', 'question': 'What is your proudest professional achievement?'},
        {'category': 'problem_solving', 'question': 'Describe a complex problem you solved.'},
        {'category': 'adaptability', 'question': 'How do you adapt to changing priorities?'},
        {'category': 'communication', 'question': 'Describe your communication style.'},
        {'category': 'culture', 'question': 'What type of work culture do you thrive in?'},
        {'category': 'salary', 'question': 'What are your salary expectations?'},
        {'category': 'availability', 'question': 'What is your notice period and availability?'},
    ]
    for q in questions:
        QuestionBank.objects.create(category=q['category'], question=q['question'])
    print(f'Seeded {len(questions)} system questions.')
else:
    print('Questions already exist, skipping.')
"

exec "$@"
