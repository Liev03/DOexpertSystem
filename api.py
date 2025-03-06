from flask import Flask, request, jsonify
from flask_cors import CORS
from experta import KnowledgeEngine, Rule, Fact, P, MATCH, TEST
import datetime
import pytz
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
        all_recommendations = [issue["recommendation"] for issue in selected_issues]
        unique_sentences = set()

        for recommendation in all_recommendations:
            sentences = recommendation.split(". ")
            for sentence in sentences:
                if sentence.strip() and sentence not in unique_sentences:  # Avoid empty strings and duplicates
                    unique_sentences.add(sentence.strip())

        # Combine sentences into a single paragraph
        self.most_relevant_recommendations = self._structure_recommendations(unique_sentences)

        # Handle positive feedback
        self.positive_messages = [feedback["message"] for feedback in self.positive_feedback]
        self.positive_suggestions = [feedback["suggestion"] for feedback in self.positive_feedback]

    def _structure_recommendations(self, sentences):
        """
        Structures the recommendations into a readable, non-redundant paragraph.
        """
        # Group related actions
        aeration_actions = []
        feeding_actions = []
        shading_actions = []
        monitoring_actions = []
        other_actions = []

        for sentence in sentences:
            if "aeration" in sentence.lower():
                aeration_actions.append(sentence)
            elif "feed" in sentence.lower() or "overfeed" in sentence.lower():
                feeding_actions.append(sentence)
            elif "shade" in sentence.lower():
                shading_actions.append(sentence)
            elif "monitor" in sentence.lower():
                monitoring_actions.append(sentence)
            else:
                other_actions.append(sentence)

        # Build the recommendation paragraph
        recommendation = []

        if aeration_actions:
            recommendation.append("Increase aeration to improve oxygen levels. " + " ".join(aeration_actions[1:]))
        if shading_actions:
            recommendation.append("Provide shade to reduce heat stress. " + " ".join(shading_actions[1:]))
        if feeding_actions:
            recommendation.append("Avoid overfeeding fish, as uneaten food can consume oxygen. " + " ".join(feeding_actions[1:]))
        if monitoring_actions:
            recommendation.append("Monitor fish behavior closely for signs of stress. " + " ".join(monitoring_actions[1:]))
        if other_actions:
            recommendation.append(" ".join(other_actions))

        # Join all parts into a single paragraph
        return ". ".join(recommendation) + "."

    def get_time_of_day(self):
        """Returns the current time period (morning, afternoon, evening, night) based on Philippine Time."""
        local_timezone = pytz.timezone("Asia/Manila")  # Set timezone to the Philippines
        now = datetime.datetime.now(local_timezone)
        hour = now.hour

        logger.debug(f"Server Time: {now.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Manila)")  # Log time for debugging

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
                           "Increase aeration at night to prevent oxygen crashes. Avoid overfeeding fish, as uneaten food can consume oxygen.", severity=4, category="oxygen")
        elif time_period == "afternoon":
            self.add_issue("⚠️ Critically low oxygen levels during the day! Fish may be lethargic or surfacing.",
                           "Immediately activate all aerators and increase water circulation. Reduce organic waste by cleaning debris and avoiding overfeeding.", severity=4, category="oxygen")
        else:
            self.add_issue("⚠️ Critically low oxygen levels! Fish may be lethargic or surfacing.",
                           "Immediately activate all aerators and increase water circulation. Reduce organic waste by cleaning debris and avoiding overfeeding.", severity=4, category="oxygen")

    @Rule(Fact(temperature=MATCH.temp & P(lambda x: x > 30)))
    def high_temperature(self, temp):
        time_period = self.get_time_of_day()
        if time_period == "afternoon":
            self.add_issue("🔥 High afternoon temperatures detected! Oxygen levels may drop.",
                           "Provide shade using floating plants or shade cloths. Increase water depth to reduce heat absorption.", severity=3, category="temperature")
        elif time_period == "morning":
            self.add_issue("🔥 High morning temperatures detected! Oxygen levels may drop.",
                           "Increase aeration to improve oxygen levels. Provide shade and monitor fish behavior for signs of stress.", severity=3, category="temperature")
        else:
            self.add_issue("🔥 High water temperature detected! Oxygen levels may drop.",
                           "Increase aeration to improve oxygen levels. Provide shade and monitor fish behavior for signs of stress.", severity=3, category="temperature")

    # === pH Rules ===
    @Rule(Fact(ph_level=MATCH.ph & P(lambda x: x < 6.5)))
    def low_ph(self, ph):
        time_period = self.get_time_of_day()
        if ph < 3.0:  # Extremely low pH
            self.add_issue("⚠️ Extremely low pH detected! Water is highly acidic and dangerous for fish.",
                           "Immediately add agricultural lime or baking soda to raise pH. Perform a partial water change to dilute acidity.", severity=5, category="ph")
        else:  # Moderately low pH
            self.add_issue("⚠️ Low pH detected! Water is too acidic.",
                           "Add agricultural lime or baking soda to gradually raise pH. Avoid sudden changes, as they can stress fish.", severity=3, category="ph")

    @Rule(Fact(ph_level=MATCH.ph & P(lambda x: x > 8.5)))
    def high_ph(self, ph):
        time_period = self.get_time_of_day()
        if time_period == "afternoon":
            self.add_issue("⚠️ High pH detected during the afternoon! Water is too alkaline.",
                           "Introduce peat moss or use pH stabilizers to lower alkalinity. Monitor pH daily to ensure gradual adjustment.", severity=3, category="ph")
        else:
            self.add_issue("⚠️ High pH detected! Water is too alkaline.",
                           "Introduce peat moss or use pH stabilizers to lower alkalinity. Monitor pH daily to ensure gradual adjustment.", severity=3, category="ph")
    
    # === Salinity Rules ===
    @Rule(Fact(salinity=MATCH.sal & P(lambda x: x > 15)))
    def high_salinity(self, sal):
        time_period = self.get_time_of_day()
        if time_period == "morning":
            self.add_issue("⚠️ High salinity detected in the morning! Potential stress on freshwater fish.",
                           "Dilute the water by adding fresh water gradually. Identify and remove sources of salt contamination.", severity=3, category="salinity")
        else:
            self.add_issue("⚠️ High salinity detected! Potential stress on freshwater fish.",
                           "Dilute the water by adding fresh water gradually. Identify and remove sources of salt contamination.", severity=3, category="salinity")

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    logger.debug(f"Received input data: {data}")  # Log input data for debugging

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
    logger.debug(f"Generated result: {result}")  # Log result for debugging
    return jsonify(result)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
