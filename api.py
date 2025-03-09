from flask import Flask, request, jsonify
from flask_cors import CORS
from experta import KnowledgeEngine, Rule, Fact, P, MATCH
import datetime
import pytz
import logging
import os

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
        self.most_relevant_warnings = []  # Initialize to avoid AttributeError
        self.most_relevant_recommendations = []  # Initialize to avoid AttributeError
        self.predictions = []  # Store predictions for each issue
        self.fish_type = "standard"  # Default fish type

    def add_issue(self, warning, recommendation, severity, category, prediction):
        """Adds an issue while ensuring diversity in categories."""
        # Check if the issue already exists to avoid duplicates
        if not any(issue["warning"] == warning for issue in self.relevant_issues):
            self.relevant_issues.append({
                "warning": warning,
                "recommendation": recommendation,
                "severity": severity,
                "category": category,
                "prediction": prediction  # Add prediction to the issue
            })

    def add_positive_feedback(self, message, suggestion, category):
        """Adds positive feedback when water parameters are within a healthy range."""
        self.positive_feedback.append({
            "message": message,
            "suggestion": suggestion,
            "category": category
        })

    def finalize_decision(self):
        """Includes all detected warnings, recommendations, and predictions."""
        if not self.relevant_issues:
            # Only show the "all parameters are optimal" message if NO issues are detected
            self.positive_feedback.append({
                "message": "✅ All water parameters are in optimal range!",
                "suggestion": "Maintain regular monitoring and continue good pond management practices.",
                "category": "overall"
            })
            self.most_relevant_warnings = []  # No warnings
            self.most_relevant_recommendations = []  # No recommendations
            self.predictions = []  # No predictions
        else:
            # Sort issues by severity (descending)
            self.relevant_issues.sort(key=lambda x: x["severity"], reverse=True)

            # Extract all warnings
            self.most_relevant_warnings = [issue["warning"] for issue in self.relevant_issues]

            # Extract all recommendations (no merging)
            self.most_relevant_recommendations = [issue["recommendation"] for issue in self.relevant_issues]

            # Extract all predictions
            self.predictions = [issue["prediction"] for issue in self.relevant_issues]

        # Handle positive feedback
        self.positive_messages = [feedback["message"] for feedback in self.positive_feedback]
        self.positive_suggestions = [feedback["suggestion"] for feedback in self.positive_feedback]

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

    # === Fish Type Rules ===
    @Rule(Fact(fish_type="standard"))
    def set_standard_fish_type(self):
        """Set fish type to standard."""
        self.fish_type = "standard"

    @Rule(Fact(fish_type="catfish"))
    def set_catfish_fish_type(self):
        """Set fish type to catfish."""
        self.fish_type = "catfish"

    @Rule(Fact(fish_type="tilapia"))
    def set_tilapia_fish_type(self):
        """Set fish type to tilapia."""
        self.fish_type = "tilapia"

    @Rule(Fact(fish_type="crayfish"))
    def set_crayfish_fish_type(self):
        """Set fish type to crayfish."""
        self.fish_type = "crayfish"

    # === pH Rules ===
    @Rule(
        Fact(ph_level=MATCH.ph & P(lambda x: x < 6.5)),
        Fact(fish_type="crayfish")
    )
    def low_ph_crayfish(self, ph):
        self.add_issue(
            "⚠️ Low pH detected! Crayfish prefer a pH between 6.5 and 7.5.",
            "Add baking soda (1/2 teaspoon per 5 gallons) to raise pH gradually.",
            severity=3,
            category="ph",
            prediction="Fish may become stressed and stop eating if pH is not corrected."
        )

    # === Temperature Rules ===
    @Rule(
        Fact(temperature=MATCH.temp & P(lambda x: x > 24)),
        Fact(fish_type="crayfish")
    )
    def high_temperature_crayfish(self, temp):
        self.add_issue(
            "⚠️ High temperature detected! Crayfish prefer temperatures between 18°C and 24°C.",
            "Provide shade and increase water circulation to cool the water.",
            severity=3,
            category="temperature",
            prediction="Fish may experience stress and reduced oxygen levels if temperatures remain high."
        )

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    logger.debug(f"Received input data: {data}")

    # Check if required keys are present
    required_keys = ["ph_level", "dissolved_oxygen", "temperature", "salinity", "ammonia"]
    for key in required_keys:
        if key not in data:
            logger.error(f"Missing key in input data: {key}")
            return jsonify({"error": f"Missing key in input data: {key}"}), 400
        if not isinstance(data[key], (int, float)):
            logger.error(f"Invalid {key} value: {data[key]}")
            return jsonify({"error": f"{key} must be a number!"}), 400
        if data[key] < 0:  # Check for negative values
            logger.error(f"Invalid {key} value: {data[key]} (must be non-negative)")
            return jsonify({"error": f"{key} must be non-negative!"}), 400

    fish_type = data.get('fish_type', 'standard')  # Default to "standard" if not specified

    predictor = OxygenPredictor()
    predictor.reset()
    predictor.declare(Fact(**data))
    predictor.declare(Fact(fish_type=fish_type))  # Declare fish_type as a fact
    predictor.run()
    predictor.finalize_decision()

    result = {
        "warnings": predictor.most_relevant_warnings,
        "recommendations": predictor.most_relevant_recommendations,
        "positive_feedback": predictor.positive_messages,
        "positive_suggestions": predictor.positive_suggestions,
        "predictions": predictor.predictions  # Add predictions to the response
    }
    logger.debug(f"Generated result: {result}")
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
