# CodeAlpha MiniSocial

A full-featured mini social media platform built with Django as part of the **CodeAlpha Web Development Internship**.

## 🚀 Live Demo

- **App:** https://mini-social-zqfp.onrender.com
- **Admin Panel:** https://mini-social-zqfp.onrender.com/panel/
- **Django Admin:** https://mini-social-zqfp.onrender.com/admin/

## ✨ Features

- 🔐 User authentication (username/email login)
- 👤 User profiles with avatar, cover, bio, phone
- 📝 Posts (text, image, video) with edit/delete
- ❤️ Likes + 6 reactions (Love, Haha, Wow, Sad, Angry)
- 💬 Nested comments & replies
- 👥 Follow system
- 🔔 Live notifications (polling)
- 💬 Direct messages (real-time)
- 📸 Stories (24-hour expiry)
- 🔖 Saved posts
- 🔍 Search users & posts
- #️⃣ Hashtags
- 👥 Suggestions ("People You May Know")
- 🌙 Dark mode
- 🎛️ Admin panel with RBAC (User/Moderator/Admin)
- 🚫 Ban system
- 📧 Email via Resend API (welcome + forgot password OTP)
- 🗄️ PostgreSQL database
- 📱 Responsive design
- ♾️ Infinite scroll

## 🛠️ Tech Stack

- **Backend:** Django 4.2.16, Python 3.11
- **Database:** PostgreSQL (production), SQLite (dev)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Deployment:** Render (Web Service + PostgreSQL)
- **Email:** Resend API
- **Server:** Gunicorn
- **Static Files:** Whitenoise

## 📦 Installation (Local Setup)

```bash
# Clone repo
git clone https://github.com/Dinesh7124/CodeAlpha_mini_social.git
cd CodeAlpha_mini_social

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver