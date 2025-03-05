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

        # Merge recommendations into a single paragraph (remove duplicates, improve flow)
        unique_recommendations = list(set(issue["recommendation"] for issue in selected_issues))
        self.most_relevant_recommendations = " ".join(unique_recommendations)

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
        if time_period == "night":
            self.add_issue("⚠️ Nighttime oxygen depletion! Risk of fish suffocation.",
                           "Increase aeration at night to prevent oxygen crashes.", severity=4, category="oxygen")
        else:
            self.add_issue("⚠️ Critically low oxygen levels! Fish may be lethargic or surfacing.",
                           "Immediately activate aerators, reduce organic waste, and increase water circulation.", severity=4, category="oxygen")

    @Rule(Fact(temperature=MATCH.temp & P(lambda x: x > 30)))
    def high_temperature(self, temp):
        time_period = self.get_time_of_day()
        if time_period == "afternoon":
            self.add_issue("🔥 High afternoon temperatures detected! Oxygen levels may drop.",
                           "Provide shade or increase water depth to reduce heat stress.", severity=3, category="temperature")
        else:
            self.add_issue("🔥 High water temperature detected! Oxygen levels may drop.",
                           "Increase aeration, provide shade, and monitor fish behavior.", severity=3, category="temperature")

    # === pH Rules ===
    @Rule(Fact(ph_level=MATCH.ph & P(lambda x: x < 6.5)))
    def low_ph(self, ph):
        self.add_issue("⚠️ Low pH detected! Water is too acidic.",
                       "Add lime or baking soda to raise pH gradually.", severity=3, category="ph")

    @Rule(Fact(ph_level=MATCH.ph & P(lambda x: x > 8.5)))
    def high_ph(self, ph):
        self.add_issue("⚠️ High pH detected! Water is too alkaline.",
                       "Introduce peat moss or use pH stabilizers to lower alkalinity.", severity=3, category="ph")
    
    # === Salinity Rules ===
    # Removed the low salinity rule since this is for freshwater systems
    @Rule(Fact(salinity=MATCH.sal & P(lambda x: x > 15)))
    def high_salinity(self, sal):
        self.add_issue("⚠️ High salinity detected! Potential stress on freshwater fish.",
                       "Dilute with fresh water to bring salinity to optimal levels.", severity=3, category="salinity")

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
