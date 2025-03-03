from flask import Flask, request, jsonify
from experta import *

app = Flask(__name__)

class WaterQuality(Fact):
    """Fact model for water quality conditions"""
    temperature = Field(float)
    pH = Field(float)
    salinity = Field(float)
    ammonia = Field(float)
    dissolved_oxygen = Field(float)
    time_of_day = Field(str)  # "day" or "night"

class OxygenPredictor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.warnings = []
        self.recommendations = []

    def add_warning(self, message):
        """Store warning messages"""
        self.warnings.append(message)

    def add_recommendation(self, message):
        """Store recommendation messages"""
        self.recommendations.append(message)

    # 🚨 Temperature & Oxygen Rules
    @Rule(WaterQuality(temperature=P(lambda t: t > 30), dissolved_oxygen=P(lambda o: o < 4)))
    def critical_oxygen_drop(self):
        self.add_warning("🚨 High temperature detected! Oxygen depletion is critical.")
        self.add_recommendation("Increase aeration and consider shading.")

    @Rule(WaterQuality(temperature=P(lambda t: t > 35), dissolved_oxygen=P(lambda o: o < 3)))
    def extreme_heat_danger(self):
        self.add_warning("🔥 Extreme heat detected! Oxygen levels critically low.")
        self.add_recommendation("Increase aeration, perform water exchange, and reduce feeding.")

    @Rule(WaterQuality(temperature=P(lambda t: t < 15)))
    def low_temp_slow_metabolism(self):
        self.add_warning("⚠️ Low temperature detected! Fish metabolism slows down.")
        self.add_recommendation("Adjust feeding schedules and monitor fish activity.")

    # 🌊 Salinity & Oxygen Rules
    @Rule(WaterQuality(salinity=P(lambda s: s > 40)))
    def high_salinity_risk(self):
        self.add_warning("⚠️ High salinity detected! Oxygen solubility decreases, increasing fish stress.")
        self.add_recommendation("Perform partial freshwater exchange.")

    @Rule(WaterQuality(temperature=P(lambda t: t > 30), salinity=P(lambda s: s > 35)))
    def high_temp_high_salinity(self):
        self.add_warning("🚨 High temperature & salinity detected! Oxygen loss is accelerated.")
        self.add_recommendation("Increase aeration and add freshwater.")

    # ☠️ Ammonia Impact on Oxygen
    @Rule(WaterQuality(ammonia=P(lambda a: a > 0.5), dissolved_oxygen=P(lambda o: o < 4)))
    def ammonia_stress_oxygen_drop(self):
        self.add_warning("🚨 High ammonia & low oxygen detected! Fish stress is critical.")
        self.add_recommendation("Perform water exchange and check for overfeeding.")

    @Rule(WaterQuality(ammonia=P(lambda a: a > 1)))
    def severe_ammonia_toxicity(self):
        self.add_warning("⚠️ Severe ammonia toxicity detected! Oxygen demand increased.")
        self.add_recommendation("Improve filtration, remove organic waste, and reduce stocking density.")

    # 🫧 Dissolved Oxygen Levels
    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 5)))
    def low_oxygen_warning(self):
        self.add_warning("🚨 Low oxygen detected! Aeration needed.")
        self.add_recommendation("Increase aeration, especially in warm weather.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 3)))
    def critical_low_oxygen(self):
        self.add_warning("🚨 Critically low oxygen! High risk of fish mortality.")
        self.add_recommendation("Emergency aeration required.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o > 10)))
    def high_oxygen_saturation(self):
        self.add_warning("⚠️ Excess oxygen detected! Risk of gas bubble disease.")
        self.add_recommendation("Reduce aeration and monitor fish behavior.")

    # 🌙 Night-Time Oxygen Depletion & Algae Effects
    @Rule(WaterQuality(time_of_day="night", dissolved_oxygen=P(lambda o: o < 5)))
    def night_oxygen_depletion(self):
        self.add_warning("⚠️ Night-time oxygen drop detected! Algae respiration may be depleting oxygen.")
        self.add_recommendation("Ensure aerators are running at night.")

    @Rule(WaterQuality(time_of_day="night", dissolved_oxygen=P(lambda o: o < 4), ammonia=P(lambda a: a > 0.7)))
    def night_algae_ammonia_risk(self):
        self.add_warning("🚨 Night-time oxygen depletion & ammonia toxicity detected! Immediate action required.")
        self.add_recommendation("Increase nighttime aeration and reduce organic waste.")

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        processed_data = {
            "temperature": float(data["temperature"]),
            "pH": float(data["pH"]),
            "salinity": float(data["salinity"]),
            "ammonia": float(data["ammonia"]),
            "dissolved_oxygen": float(data["dissolved_oxygen"]),
            "time_of_day": data["time_of_day"].lower()
        }

        if processed_data["time_of_day"] not in ["day", "night"]:
            return jsonify({"error": "Invalid time_of_day. Use 'day' or 'night'."}), 400

    except (ValueError, TypeError, KeyError):
        return jsonify({"error": "Invalid input data format"}), 400

    # Run expert system
    engine = OxygenPredictor()
    engine.reset()
    engine.declare(WaterQuality(**processed_data))
    engine.run()

    return jsonify({"warnings": engine.warnings, "recommendations": engine.recommendations})

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    app.run(host="0.0.0.0", port=port)
