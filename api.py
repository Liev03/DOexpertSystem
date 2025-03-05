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
        self.issues = []  # Stores detected issues

    def add_issue(self, warning, recommendation, severity, category):
        """Adds an issue while ensuring diversity in categories."""
        self.issues.append({
            "warning": warning,
            "recommendation": recommendation,
            "severity": severity,
            "category": category
        })

    def finalize_decision(self):
        """Groups issues by category and merges their recommendations."""
        if not self.issues:
            return {
                "warnings": ["✅ All water parameters are in optimal range!"],
                "recommendations": ["Maintain regular monitoring and continue good pond management practices."]
            }

        # Sort by severity and group by category
        self.issues.sort(key=lambda x: x["severity"], reverse=True)
        grouped_issues = {}

        for issue in self.issues:
            category = issue["category"]
            if category in grouped_issues:
                grouped_issues[category]["warning"] += f" {issue['warning']}"
                grouped_issues[category]["recommendation"] += f" {issue['recommendation']}"
            else:
                grouped_issues[category] = issue

        # Convert to a list format for API response
        merged_issues = list(grouped_issues.values())
        return {
            "warnings": [issue["warning"] for issue in merged_issues],
            "recommendations": [issue["recommendation"] for issue in merged_issues]
        }

    def get_time_of_day(self):
        """Returns the current time period (morning, afternoon, evening, night) based on Philippine Time."""
        local_timezone = pytz.timezone("Asia/Manila")
        now = datetime.datetime.now(local_timezone)
        hour = now.hour

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

    @Rule(Fact(dissolved_oxygen=MATCH.do & P(lambda x: 2.5 <= x < 5)))
    def low_oxygen(self, do):
        self.add_issue("📉 Oxygen is lower than ideal. Fish may experience mild stress.",
                       "Increase aeration and monitor oxygen levels during warm periods.", severity=3, category="oxygen")

    # === Temperature Rules ===
    @Rule(Fact(temperature=MATCH.temp & P(lambda x: x > 30)))
    def high_temperature(self, temp):
        time_period = self.get_time_of_day()
        if time_period == "afternoon":
            self.add_issue("🔥 High afternoon temperatures detected! Oxygen levels may drop.",
                           "Provide shade or increase water depth to reduce heat stress.", severity=3, category="temperature")
        elif time_period == "night":
            self.add_issue("🔥 High water temperature detected at night! Risk of fish stress.",
                           "Increase aeration and ensure proper water circulation to maintain oxygen levels.", severity=3, category="temperature")
        else:
            self.add_issue("🔥 High water temperature detected! Oxygen levels may drop.",
                           "Increase aeration and monitor fish behavior.", severity=3, category="temperature")

    # === Ammonia Rules ===
    @Rule(Fact(ammonia=MATCH.amm & P(lambda x: x > 0.5)))
    def high_ammonia(self, amm):
        self.add_issue("☠️ High ammonia levels detected! Fish health is at risk.",
                       "Perform partial water changes, clean filters, and monitor feed intake.", severity=5, category="ammonia")

    # === Oxygen Trend Rules ===
    @Rule(Fact(previous_do=MATCH.prev_do), Fact(dissolved_oxygen=MATCH.current_do), 
          TEST(lambda prev_do, current_do: current_do < prev_do - 1))
    def oxygen_declining(self, current_do, prev_do):
        self.add_issue("⚠️ Oxygen levels are dropping! Preventive action needed.",
                       "Monitor aeration systems and avoid overstocking.", severity=3, category="oxygen")

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    predictor = OxygenPredictor()
    predictor.reset()
    predictor.declare(Fact(**data))
    predictor.run()
    result = predictor.finalize_decision()
    return jsonify(result)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
