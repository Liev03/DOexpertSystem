from flask import Flask, request, jsonify
from flask_cors import CORS
from experta import KnowledgeEngine, Rule, Fact, P, MATCH, TEST
import datetime
import pytz

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

class OxygenPredictor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.relevant_issues = []  # Stores detected issues
        self.positive_feedback = []  # Stores positive messages

    def add_issue(self, warning, recommendation, severity, category):
        """Adds an issue while ensuring diversity in categories."""
        self.relevant_issues.append({
            "warning": warning,
            "recommendation": recommendation,
            "severity": severity,
            "category": category
        })
    
    def add_positive_feedback(self, message, suggestion, category):
        """Adds positive feedback when water parameters are within a healthy range."""
        self.positive_feedback.append({
            "message": message,
            "suggestion": suggestion,
            "category": category
        })

    def finalize_decision(self):
        """Selects two most relevant warnings and merges their recommendations into one."""
        if not self.relevant_issues:
            self.positive_feedback.append({
                "message": "✅ All water parameters are in optimal range!",
                "suggestion": "Maintain regular monitoring and continue good pond management practices.",
                "category": "overall"
            })

        # Sort issues by severity (descending)
        self.relevant_issues.sort(key=lambda x: x["severity"], reverse=True)
        selected_issues = []
        seen_categories = set()
        
        for issue in self.relevant_issues:
            if issue["category"] not in seen_categories:
                selected_issues.append(issue)
                seen_categories.add(issue["category"])
            if len(selected_issues) == 2:
                break

        # Extract warnings
        self.most_relevant_warnings = [issue["warning"] for issue in selected_issues]

        # Merge recommendations smartly
        unique_recommendations = set()
        for issue in selected_issues:
            for rec in issue["recommendation"].split('. '):
                unique_recommendations.add(rec)
        self.most_relevant_recommendations = '. '.join(unique_recommendations) + '.'

        # Handle positive feedback
        self.positive_messages = [feedback["message"] for feedback in self.positive_feedback]
        self.positive_suggestions = [feedback["suggestion"] for feedback in self.positive_feedback]

    def get_time_of_day(self):
        """Returns the current time period (morning, afternoon, evening, night) based on Philippine Time."""
        local_timezone = pytz.timezone("Asia/Manila")  # Set timezone to the Philippines
        now = datetime.datetime.now(local_timezone)
        hour = now.hour

        print(f"Server Time: {now.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Manila)")  # Log time for debugging

        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 20:
            return "evening"
        else:
            return "night"

    # === Oxygen Rules ===
    @Rule(Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 2.5)))
    def critically_low_oxygen(self, do):
        time_period = self.get_time_of_day()
        warning = "⚠️ Critically low oxygen levels! Fish may be lethargic or surfacing."
        recommendation = "Immediately activate aerators, reduce organic waste, and increase water circulation."
        
        if time_period == "night":
            warning = "⚠️ Nighttime oxygen depletion! Risk of fish suffocation."
            recommendation = "Increase aeration at night to prevent oxygen crashes."
        
        self.add_issue(warning, recommendation, severity=4, category="oxygen")

    @Rule(Fact(dissolved_oxygen=MATCH.do & P(lambda x: 2.5 <= x < 5)))
    def low_oxygen(self, do):
        self.add_issue("📉 Oxygen is lower than ideal. Fish may experience mild stress.",
                       "Increase aeration and monitor oxygen levels during warm periods.", severity=3, category="oxygen")

    @Rule(Fact(dissolved_oxygen=MATCH.do & P(lambda x: 5 <= x <= 8)))
    def optimal_oxygen(self, do):
        self.add_positive_feedback("✅ Oxygen levels are within the optimal range!", 
                                   "Maintain proper aeration and minimize excessive organic waste.", category="oxygen")
    
    @Rule(Fact(dissolved_oxygen=MATCH.do & P(lambda x: x > 8)))
    def excessive_oxygen(self, do):
        self.add_issue("🌊 Excessive dissolved oxygen detected! Potential gas bubble disease risk.",
                       "Reduce aeration and monitor fish closely for signs of stress.", severity=2, category="oxygen")

    # === Temperature Rules ===
    @Rule(Fact(temperature=MATCH.temp & P(lambda x: x > 30)))
    def high_temperature(self, temp):
        time_period = self.get_time_of_day()
        warning = "🔥 High water temperature detected! Oxygen levels may drop."
        recommendation = "Increase aeration, provide shade, and monitor fish behavior."
        
        if time_period == "afternoon":
            warning = "🔥 High afternoon temperatures detected! Oxygen levels may drop."
            recommendation = "Provide shade or increase water depth to reduce heat stress."
        
        self.add_issue(warning, recommendation, severity=3, category="temperature")

    # === Ammonia Rules ===
    @Rule(Fact(ammonia=MATCH.amm & P(lambda x: x > 0.5)))
    def high_ammonia(self, amm):
        self.add_issue("☠️ High ammonia levels detected! Fish health is at risk.",
                       "Perform partial water changes, clean filters, and monitor feed intake.", severity=5, category="ammonia")

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    predictor = OxygenPredictor()
    predictor.reset()
    predictor.declare(Fact(**data))
    predictor.run()
    predictor.finalize_decision()

    result = {
        "warnings": predictor.most_relevant_warnings,
        "recommendations": [predictor.most_relevant_recommendations],
        "positive_feedback": predictor.positive_messages,
        "positive_suggestions": predictor.positive_suggestions
    }
    return jsonify(result)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
