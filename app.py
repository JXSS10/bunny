import os
from flask import Flask, render_template, request, jsonify # تأكد من وجود render_template
# ... (باقي الاستيرادات)

app = Flask(__name__)

# ... (باقي الكود مثل الإعدادات والدوال المساعدة) ...

@app.route('/')
def home():
    # يجب أن تكون هذه هي الطريقة لعرض ملف HTML
    return render_template('bunny1.html')

# ... (باقي المسارات مثل /analyze, /download, etc.) ...

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
