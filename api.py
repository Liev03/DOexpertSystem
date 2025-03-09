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

    # === Oxygen Rules ===
    @Rule(
        Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 6)),
        Fact(fish_type="standard")
    )
    def critically_low_oxygen_standard(self, do):
        time_period = self.get_time_of_day()
        if time_period == "night":
            self.add_issue(
                "⚠️ Nighttime oxygen depletion! Risk of fish suffocation.",
                "Increase water circulation at night to prevent oxygen crashes. Avoid overfeeding fish, as uneaten food can consume oxygen.",
                severity=4,
                category="oxygen",
                prediction="Fish may suffocate and die if oxygen levels remain critically low."
            )
        else:
            self.add_issue(
                "⚠️ Critically low oxygen levels! Fish may be lethargic or surfacing.",
                "Immediately activate all aerators if available and increase water circulation. Reduce organic waste by cleaning debris and avoiding overfeeding.",
                severity=4,
                category="oxygen",
                prediction="Fish may become lethargic, stop eating, and eventually die if oxygen levels are not increased."
            )

    @Rule(
        Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 4)),
        Fact(fish_type="catfish")
    )
    def critically_low_oxygen_catfish(self, do):
        self.add_issue(
            "⚠️ Low oxygen levels detected! Catfish prefer oxygen levels above 4 ppm.",
            "Increase aeration and water circulation to improve oxygen levels.",
            severity=4,
            category="oxygen",
            prediction="Fish may become lethargic and stop eating if oxygen levels remain low."
        )

    @Rule(
        Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 5)),
        Fact(fish_type="tilapia")
    )
    def critically_low_oxygen_tilapia(self, do):
        self.add_issue(
            "⚠️ Low oxygen levels detected! Tilapia prefer oxygen levels above 5 ppm.",
            "Increase aeration and water circulation to improve oxygen levels.",
            severity=4,
            category="oxygen",
            prediction="Fish may become lethargic and stop eating if oxygen levels remain low."
        )

    @Rule(
        Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 5)),
        Fact(fish_type="crayfish")
    )
    def critically_low_oxygen_crayfish(self, do):
        self.add_issue(
            "⚠️ Low oxygen levels detected! Crayfish prefer oxygen levels above 5 ppm.",
            "Increase aeration and water circulation to improve oxygen levels.",
            severity=4,
            category="oxygen",
            prediction="Fish may become lethargic and stop eating if oxygen levels remain low."
        )

    # === Temperature Rules ===
    @Rule(
        Fact(temperature=MATCH.temp & P(lambda x: x > 27)),
        Fact(fish_type="standard")
    )
    def high_temperature_standard(self, temp):
        time_period = self.get_time_of_day()
        if time_period == "morning":
            self.add_issue(
                "🔥 High morning temperatures detected! Oxygen levels may drop.",
                "Provide shade using floating plants or shade cloths. Increase water depth to reduce heat absorption.",
                severity=3,
                category="temperature",
                prediction="High temperatures can reduce oxygen levels, stressing fish and making them more susceptible to diseases."
            )
        elif time_period == "afternoon":
            self.add_issue(
                "🔥 High afternoon temperatures detected! Oxygen levels may drop.",
                "Provide shade using floating plants or shade cloths. Increase water depth to reduce heat absorption.",
                severity=3,
                category="temperature",
                prediction="Prolonged high temperatures can lead to fish stress, reduced appetite, and increased mortality."
            )
        elif time_period == "evening":
            self.add_issue(
                "🔥 High evening temperatures detected! Oxygen levels may drop.",
                "Increase aeration and water circulation to cool the water. Avoid direct sunlight exposure.",
                severity=3,
                category="temperature",
                prediction="Fish may become stressed and lethargic if water temperatures remain high."
            )
        else:  # Nighttime
            self.add_issue(
                "🔥 High nighttime temperatures detected! Oxygen levels may drop.",
                "Increase aeration and water circulation to cool the water. Monitor fish behavior for signs of stress.",
                severity=3,
                category="temperature",
                prediction="Fish may experience stress and reduced oxygen levels, leading to potential fatalities."
            )

    @Rule(
        Fact(temperature=MATCH.temp & P(lambda x: x > 32)),
        Fact(fish_type="catfish")
    )
    def high_temperature_catfish(self, temp):
        self.add_issue(
            "⚠️ High temperature detected! Catfish prefer temperatures between 25°C and 32°C.",
            "Provide shade and increase water circulation to cool the water.",
            severity=3,
            category="temperature",
            prediction="Fish may experience stress and reduced oxygen levels if temperatures remain high."
        )

    @Rule(
        Fact(temperature=MATCH.temp & P(lambda x: x > 30)),
        Fact(fish_type="tilapia")
    )
    def high_temperature_tilapia(self, temp):
        self.add_issue(
            "⚠️ High temperature detected! Tilapia prefer temperatures between 26°C and 30°C.",
            "Provide shade and increase water circulation to cool the water.",
            severity=3,
            category="temperature",
            prediction="Fish may experience stress and reduced oxygen levels if temperatures remain high."
        )

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

    # === pH Rules ===
    @Rule(
        Fact(ph_level=MATCH.ph & P(lambda x: x < 5)),
        Fact(fish_type="standard")
    )
    def low_ph_standard(self, ph):
        if ph < 3.0:  # Extremely low pH
            self.add_issue(
                "⚠️ Extremely low pH detected! Water is highly acidic and dangerous for fish.",
                "Immediately add baking soda (1 teaspoon per 5 gallons) to raise pH and perform a partial water change to reduce acidity.",
                severity=5,
                category="ph",
                prediction="Fish may experience severe stress, tissue damage, and death if pH remains extremely low."
            )
        else:  # Moderately low pH
            self.add_issue(
                "⚠️ Low pH detected! Water is too acidic.",
                "Add baking soda (1/2 teaspoon per 5 gallons) to raise pH gradually and perform a partial water change to dilute acidity.",
                severity=3,
                category="ph",
                prediction="Fish may become stressed, stop eating, and develop health issues if pH is not corrected."
            )

    @Rule(
        Fact(ph_level=MATCH.ph & P(lambda x: x < 6.5)),
        Fact(fish_type="catfish")
    )
    def low_ph_catfish(self, ph):
        self.add_issue(
            "⚠️ Low pH detected! Catfish prefer a pH between 6.5 and 8.0.",
            "Add baking soda (1/2 teaspoon per 5 gallons) to raise pH gradually.",
            severity=3,
            category="ph",
            prediction="Fish may become stressed and stop eating if pH is not corrected."
        )

    @Rule(
        Fact(ph_level=MATCH.ph & P(lambda x: x < 6.5)),
        Fact(fish_type="tilapia")
    )
    def low_ph_tilapia(self, ph):
        self.add_issue(
            "⚠️ Low pH detected! Tilapia prefer a pH between 6.5 and 8.5.",
            "Add baking soda (1/2 teaspoon per 5 gallons) to raise pH gradually.",
            severity=3,
            category="ph",
            prediction="Fish may become stressed and stop eating if pH is not corrected."
        )

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

    @Rule(
        Fact(ph_level=MATCH.ph & P(lambda x: x > 8.5)),
        Fact(fish_type="standard")
    )
    def high_ph_standard(self, ph):
        self.add_issue(
            "⚠️ High pH detected! Water is too alkaline.",
            "Add driftwood or peat moss to the tank to naturally lower pH and perform a partial water change to reduce alkalinity.",
            severity=3,
            category="ph",
            prediction="Fish may experience stress, reduced growth, and increased susceptibility to diseases if pH remains high."
        )

    @Rule(
        Fact(ph_level=MATCH.ph & P(lambda x: x > 8.0)),
        Fact(fish_type="catfish")
    )
    def high_ph_catfish(self, ph):
        self.add_issue(
            "⚠️ High pH detected! Catfish prefer a pH between 6.5 and 8.0.",
            "Add driftwood or peat moss to the tank to naturally lower pH.",
            severity=3,
            category="ph",
            prediction="Fish may experience stress and reduced growth if pH remains high."
        )

    @Rule(
        Fact(ph_level=MATCH.ph & P(lambda x: x > 8.5)),
        Fact(fish_type="tilapia")
    )
    def high_ph_tilapia(self, ph):
        self.add_issue(
            "⚠️ High pH detected! Tilapia prefer a pH between 6.5 and 8.5.",
            "Add driftwood or peat moss to the tank to naturally lower pH.",
            severity=3,
            category="ph",
            prediction="Fish may experience stress and reduced growth if pH remains high."
        )

    @Rule(
        Fact(ph_level=MATCH.ph & P(lambda x: x > 7.5)),
        Fact(fish_type="crayfish")
    )
    def high_ph_crayfish(self, ph):
        self.add_issue(
            "⚠️ High pH detected! Crayfish prefer a pH between 6.5 and 7.5.",
            "Add driftwood or peat moss to the tank to naturally lower pH.",
            severity=3,
            category="ph",
            prediction="Fish may experience stress and reduced growth if pH remains high."
        )

    # === Salinity Rules ===
    @Rule(
        Fact(salinity=MATCH.sal & P(lambda x: x > 0.3)),
        Fact(fish_type="standard")
    )
    def high_salinity_standard(self, sal):
        time_period = self.get_time_of_day()
        self.add_issue(
            f"⚠️ High salinity detected{' in the ' + time_period if time_period else ''}! Potential stress on freshwater fish.",
            "Dilute the water by adding fresh water gradually. Identify and remove sources of salt contamination.",
            severity=3,
            category="salinity",
            prediction="Freshwater fish may experience osmotic stress, leading to dehydration and death if salinity remains high."
        )

    @Rule(
        Fact(salinity=MATCH.sal & P(lambda x: x > 5)),
        Fact(fish_type="catfish")
    )
    def high_salinity_catfish(self, sal):
        self.add_issue(
            "⚠️ High salinity detected! Catfish prefer salinity levels below 5 ppt.",
            "Dilute the water by adding fresh water gradually.",
            severity=3,
            category="salinity",
            prediction="Fish may experience osmotic stress if salinity remains high."
        )

    @Rule(
        Fact(salinity=MATCH.sal & P(lambda x: x > 5)),
        Fact(fish_type="tilapia")
    )
    def high_salinity_tilapia(self, sal):
        self.add_issue(
            "⚠️ High salinity detected! Tilapia prefer salinity levels below 5 ppt.",
            "Dilute the water by adding fresh water gradually.",
            severity=3,
            category="salinity",
            prediction="Fish may experience osmotic stress if salinity remains high."
        )

    @Rule(
        Fact(salinity=MATCH.sal & P(lambda x: x > 1)),
        Fact(fish_type="crayfish")
    )
    def high_salinity_crayfish(self, sal):
        self.add_issue(
            "⚠️ High salinity detected! Crayfish prefer salinity levels below 1 ppt.",
            "Dilute the water by adding fresh water gradually.",
            severity=3,
            category="salinity",
            prediction="Fish may experience osmotic stress if salinity remains high."
        )

    # === Ammonia Rules ===
    @Rule(
        Fact(ammonia=MATCH.amm & P(lambda x: x > 0.5)),
        Fact(fish_type="standard")
    )
    def high_ammonia_standard(self, amm):
        if amm > 1.5:  # Extremely high ammonia
            self.add_issue(
                "⚠️ Extremely high ammonia levels detected! Toxic to fish.",
                "Immediately perform a partial water change to reduce ammonia levels. Increase aeration and reduce feeding to minimize ammonia production.",
                severity=5,
                category="ammonia",
                prediction="Fish may suffer from ammonia poisoning, leading to gill damage, lethargy, and death."
            )
        else:  # Moderately high ammonia
            self.add_issue(
                "⚠️ High ammonia levels detected! Potential stress on fish.",
                "Perform a partial water change and increase aeration. Reduce feeding and remove any decaying organic matter.",
                severity=4,
                category="ammonia",
                prediction="Fish may experience stress, reduced appetite, and increased susceptibility to diseases if ammonia levels remain high."
            )

    @Rule(
        Fact(ammonia=MATCH.amm & P(lambda x: x > 3)),
        Fact(fish_type="catfish")
    )
    def high_ammonia_catfish(self, amm):
        self.add_issue(
            "⚠️ High ammonia levels detected! Catfish prefer ammonia levels below 3 ppm.",
            "Perform a partial water change and increase aeration to reduce ammonia levels.",
            severity=4,
            category="ammonia",
            prediction="Fish may suffer from ammonia poisoning if levels remain high."
        )

    @Rule(
        Fact(ammonia=MATCH.amm & P(lambda x: x > 2)),
        Fact(fish_type="tilapia")
    )
    def high_ammonia_tilapia(self, amm):
        self.add_issue(
            "⚠️ High ammonia levels detected! Tilapia prefer ammonia levels below 2 ppm.",
            "Perform a partial water change and increase aeration to reduce ammonia levels.",
            severity=4,
            category="ammonia",
            prediction="Fish may suffer from ammonia poisoning if levels remain high."
        )

    @Rule(
        Fact(ammonia=MATCH.amm & P(lambda x: x > 1)),
        Fact(fish_type="crayfish")
    )
    def high_ammonia_crayfish(self, amm):
        self.add_issue(
            "⚠️ High ammonia levels detected! Crayfish prefer ammonia levels below 1 ppm.",
            "Perform a partial water change and increase aeration to reduce ammonia levels.",
            severity=4,
            category="ammonia",
            prediction="Fish may suffer from ammonia poisoning if levels remain high."
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
