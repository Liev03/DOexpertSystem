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

    # === Fish Type Rule ===
    @Rule(Fact(type=MATCH.type))
    def set_fish_type(self, type):
        """Set the fish type and adjust rules accordingly."""
        self.fish_type = type
        logger.debug(f"Fish type set to: {type}")

    # === Oxygen Rules ===
    @Rule(
        Fact(fish_type="catfish"),
        Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 4))  # Catfish require higher oxygen levels
    )
    def critically_low_oxygen_catfish(self, do):
        self.add_issue(
            "⚠️ Critically low oxygen levels for catfish! Risk of suffocation.",
            "Increase aeration immediately and reduce stocking density.",
            severity=5,
            category="oxygen",
            prediction="Catfish may suffocate and die if oxygen levels remain critically low."
        )

    @Rule(
        Fact(fish_type="tilapia"),
        Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 5))  # Tilapia can tolerate lower oxygen levels
    )
    def critically_low_oxygen_tilapia(self, do):
        self.add_issue(
            "⚠️ Low oxygen levels for tilapia! Fish may become stressed.",
            "Increase aeration and reduce feeding to minimize oxygen consumption.",
            severity=4,
            category="oxygen",
            prediction="Tilapia may become lethargic and stop eating if oxygen levels remain low."
        )

    @Rule(
        Fact(fish_type="crayfish"),
        Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 5))  # Crayfish require moderate oxygen levels
    )
    def critically_low_oxygen_crayfish(self, do):
        self.add_issue(
            "⚠️ Low oxygen levels for crayfish! Risk of molting issues.",
            "Increase aeration and ensure proper water circulation.",
            severity=4,
            category="oxygen",
            prediction="Crayfish may experience molting problems and stress if oxygen levels remain low."
        )

    @Rule(
        Fact(fish_type="standard"),
        Fact(dissolved_oxygen=MATCH.do & P(lambda x: x < 6))  # Standard oxygen rule
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

    # === Temperature Rules ===
    @Rule(
        Fact(fish_type="catfish"),
        Fact(temperature=MATCH.temp & P(lambda x: x < 25 or x > 32))  # Catfish prefer 22-30°C
    )
    def temperature_catfish(self, temp):
        if temp < 25:
            self.add_issue(
                "⚠️ Low temperature for catfish! Fish may become lethargic.",
                "Gradually increase water temperature using a heater.",
                severity=3,
                category="temperature",
                prediction="Catfish may stop eating and become susceptible to diseases if temperatures remain low."
            )
        else:
            self.add_issue(
                "⚠️ High temperature for catfish! Risk of stress and disease.",
                "Provide shade and increase water circulation to cool the water.",
                severity=4,
                category="temperature",
                prediction="Catfish may experience stress and reduced growth if temperatures remain high."
            )

    @Rule(
        Fact(fish_type="tilapia"),
        Fact(temperature=MATCH.temp & P(lambda x: x < 26 or x > 30))  # Tilapia prefer 20-35°C
    )
    def temperature_tilapia(self, temp):
        if temp < 26:
            self.add_issue(
                "⚠️ Low temperature for tilapia! Fish may become inactive.",
                "Gradually increase water temperature using a heater.",
                severity=3,
                category="temperature",
                prediction="Tilapia may stop eating and become susceptible to diseases if temperatures remain low."
            )
        else:
            self.add_issue(
                "⚠️ High temperature for tilapia! Risk of stress and disease.",
                "Provide shade and increase water circulation to cool the water.",
                severity=4,
                category="temperature",
                prediction="Tilapia may experience stress and reduced growth if temperatures remain high."
            )

    @Rule(
        Fact(fish_type="crayfish"),
        Fact(temperature=MATCH.temp & P(lambda x: x < 18 or x > 24))  # Crayfish prefer 18-25°C
    )
    def temperature_crayfish(self, temp):
        if temp < 18:
            self.add_issue(
                "⚠️ Low temperature for crayfish! Molting may be affected.",
                "Gradually increase water temperature using a heater.",
                severity=3,
                category="temperature",
                prediction="Crayfish may experience molting issues and stress if temperatures remain low."
            )
        else:
            self.add_issue(
                "⚠️ High temperature for crayfish! Risk of stress and disease.",
                "Provide shade and increase water circulation to cool the water.",
                severity=4,
                category="temperature",
                prediction="Crayfish may experience stress and reduced growth if temperatures remain high."
            )

    @Rule(
        Fact(fish_type="standard"),
        Fact(temperature=MATCH.temp & P(lambda x: x > 27))
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
        Fact(fish_type="standard"),
        Fact(temperature=MATCH.temp & P(lambda x: x < 24))
    )
    def low_temperature_standard(self, temp):
        self.add_issue(
            "⚠️ Low temperature detected! Fish may become lethargic.",
            "Increase water temperature gradually using a heater or by reducing water flow.",
            severity=3,
            category="temperature",
            prediction="Fish may become lethargic, stop eating, and become more susceptible to diseases if temperatures remain low."
        )

    # === pH Rules ===
    @Rule(
        Fact(fish_type="catfish"),
        Fact(ph_level=MATCH.ph & P(lambda x: x < 6.5 or x > 8))  # Catfish prefer pH 6.5-8.5
    )
    def ph_catfish(self, ph):
        if ph < 6.5:
            self.add_issue(
                "⚠️ Low pH for catfish! Water is too acidic.",
                "Add baking soda to gradually raise pH.",
                severity=3,
                category="ph",
                prediction="Catfish may become stressed and stop eating if pH remains low."
            )
        else:
            self.add_issue(
                "⚠️ High pH for catfish! Water is too alkaline.",
                "Add peat moss to gradually lower pH.",
                severity=3,
                category="ph",
                prediction="Catfish may experience stress and reduced growth if pH remains high."
            )

    @Rule(
        Fact(fish_type="tilapia"),
        Fact(ph_level=MATCH.ph & P(lambda x: x < 6.5 or x > 8.5))  # Tilapia prefer pH 6-9
    )
    def ph_tilapia(self, ph):
        if ph < 6:
            self.add_issue(
                "⚠️ Low pH for tilapia! Water is too acidic.",
                "Add baking soda to gradually raise pH.",
                severity=3,
                category="ph",
                prediction="Tilapia may become stressed and stop eating if pH remains low."
            )
        else:
            self.add_issue(
                "⚠️ High pH for tilapia! Water is too alkaline.",
                "Add peat moss to gradually lower pH.",
                severity=3,
                category="ph",
                prediction="Tilapia may experience stress and reduced growth if pH remains high."
            )

    @Rule(
        Fact(fish_type="crayfish"),
        Fact(ph_level=MATCH.ph & P(lambda x: x < 6.5 or x > 7.5))  # Crayfish prefer pH 7-8.5
    )
    def ph_crayfish(self, ph):
        if ph < 6.5:
            self.add_issue(
                "⚠️ Low pH for crayfish! Water is too acidic.",
                "Add baking soda to gradually raise pH.",
                severity=3,
                category="ph",
                prediction="Crayfish may experience molting issues and stress if pH remains low."
            )
        else:
            self.add_issue(
                "⚠️ High pH for crayfish! Water is too alkaline.",
                "Add peat moss to gradually lower pH.",
                severity=3,
                category="ph",
                prediction="Crayfish may experience stress and reduced growth if pH remains high."
            )

    @Rule(
        Fact(fish_type="standard"),
        Fact(ph_level=MATCH.ph & P(lambda x: x < 5))
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
        Fact(fish_type="standard"),
        Fact(ph_level=MATCH.ph & P(lambda x: x > 8.5))
    )
    def high_ph_standard(self, ph):
        self.add_issue(
            "⚠️ High pH detected! Water is too alkaline.",
            "Add driftwood or peat moss to the tank to naturally lower pH and perform a partial water change to reduce alkalinity.",
            severity=3,
            category="ph",
            prediction="Fish may experience stress, reduced growth, and increased susceptibility to diseases if pH remains high."
        )

    # === Ammonia Rules ===
    @Rule(
        Fact(fish_type="catfish"),
        Fact(ammonia=MATCH.amm & P(lambda x: x > 3))  # Catfish are sensitive to ammonia
    )
    def ammonia_catfish(self, amm):
        if amm > 4.5:
            self.add_issue(
                "⚠️ Extremely high ammonia levels for catfish! Toxic to fish.",
                "Immediately perform a partial water change and increase aeration.",
                severity=5,
                category="ammonia",
                prediction="Catfish may suffer from ammonia poisoning, leading to gill damage and death."
            )
        else:
            self.add_issue(
                "⚠️ High ammonia levels for catfish! Potential stress on fish.",
                "Perform a partial water change and reduce feeding to minimize ammonia production.",
                severity=4,
                category="ammonia",
                prediction="Catfish may experience stress and reduced appetite if ammonia levels remain high."
            )

    @Rule(
        Fact(fish_type="tilapia"),
        Fact(ammonia=MATCH.amm & P(lambda x: x > 2.0))  # Tilapia can tolerate slightly higher ammonia levels
    )
    def ammonia_tilapia(self, amm):
        if amm > 3.0:
            self.add_issue(
                "⚠️ Extremely high ammonia levels for tilapia! Toxic to fish.",
                "Immediately perform a partial water change and increase aeration.",
                severity=5,
                category="ammonia",
                prediction="Tilapia may suffer from ammonia poisoning, leading to gill damage and death."
            )
        else:
            self.add_issue(
                "⚠️ High ammonia levels for tilapia! Potential stress on fish.",
                "Perform a partial water change and reduce feeding to minimize ammonia production.",
                severity=4,
                category="ammonia",
                prediction="Tilapia may experience stress and reduced appetite if ammonia levels remain high."
            )

    @Rule(
        Fact(fish_type="crayfish"),
        Fact(ammonia=MATCH.amm & P(lambda x: x > 1.0))  # Crayfish are sensitive to ammonia
    )
    def ammonia_crayfish(self, amm):
        if amm > 2.0:
            self.add_issue(
                "⚠️ Extremely high ammonia levels for crayfish! Toxic to crayfish.",
                "Immediately perform a partial water change and increase aeration.",
                severity=5,
                category="ammonia",
                prediction="Crayfish may suffer from ammonia poisoning, leading to molting issues and death."
            )
        else:
            self.add_issue(
                "⚠️ High ammonia levels for crayfish! Potential stress on crayfish.",
                "Perform a partial water change and reduce feeding to minimize ammonia production.",
                severity=4,
                category="ammonia",
                prediction="Crayfish may experience stress and molting problems if ammonia levels remain high."
            )

    @Rule(
        Fact(fish_type="standard"),
        Fact(ammonia=MATCH.amm & P(lambda x: x > 0.5))
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

    # === Salinity Rules ===
    @Rule(
        Fact(fish_type="catfish"),
        Fact(salinity=MATCH.sal & P(lambda x: x > 5))  # Catfish prefer low salinity
    )
    def salinity_catfish(self, sal):
        self.add_issue(
            "⚠️ High salinity for catfish! Potential stress on fish.",
            "Dilute the water by adding fresh water gradually. Identify and remove sources of salt contamination.",
            severity=3,
            category="salinity",
            prediction="Catfish may experience osmotic stress, leading to dehydration and death if salinity remains high."
        )

    @Rule(
        Fact(fish_type="tilapia"),
        Fact(salinity=MATCH.sal & P(lambda x: x > 5))  # Tilapia can tolerate moderate salinity
    )
    def salinity_tilapia(self, sal):
        self.add_issue(
            "⚠️ High salinity for tilapia! Potential stress on fish.",
            "Dilute the water by adding fresh water gradually. Identify and remove sources of salt contamination.",
            severity=3,
            category="salinity",
            prediction="Tilapia may experience osmotic stress, leading to dehydration and death if salinity remains high."
        )

    @Rule(
        Fact(fish_type="crayfish"),
        Fact(salinity=MATCH.sal & P(lambda x: x > 1.0))  # Crayfish prefer low salinity
    )
    def salinity_crayfish(self, sal):
        self.add_issue(
            "⚠️ High salinity for crayfish! Potential stress on crayfish.",
            "Dilute the water by adding fresh water gradually. Identify and remove sources of salt contamination.",
            severity=3,
            category="salinity",
            prediction="Crayfish may experience osmotic stress, leading to dehydration and death if salinity remains high."
        )

    @Rule(
        Fact(fish_type="standard"),
        Fact(salinity=MATCH.sal & P(lambda x: x > 0.3))
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

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    logger.debug(f"Received input data: {data}")

    # Check if required keys are present
    required_keys = ["ph_level", "dissolved_oxygen", "temperature", "salinity", "ammonia", "type"]
    for key in required_keys:
        if key not in data:
            logger.error(f"Missing key in input data: {key}")
            return jsonify({"error": f"Missing key in input data: {key}"}), 400
        if key != "type" and not isinstance(data[key], (int, float)):
            logger.error(f"Invalid {key} value: {data[key]}")
            return jsonify({"error": f"{key} must be a number!"}), 400
        if key != "type" and data[key] < 0:  # Check for negative values
            logger.error(f"Invalid {key} value: {data[key]} (must be non-negative)")
            return jsonify({"error": f"{key} must be non-negative!"}), 400

    # Validate fish type
    valid_fish_types = ["catfish", "tilapia", "crayfish", "standard"]
    if data["type"] not in valid_fish_types:
        logger.error(f"Invalid fish type: {data['type']}")
        return jsonify({"error": f"Invalid fish type. Must be one of: {valid_fish_types}"}), 400

    predictor = OxygenPredictor()
    predictor.reset()
    predictor.declare(Fact(**data))
    predictor.run()
    predictor.finalize_decision()

    result = {
        "warnings": predictor.most_relevant_warnings,
        "recommendations": predictor.most_relevant_recommendations,
        "positive_feedback": predictor.positive_messages,
        "positive_suggestions": predictor.positive_suggestions,
        "predictions": predictor.predictions
    }
    logger.debug(f"Generated result: {result}")
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
