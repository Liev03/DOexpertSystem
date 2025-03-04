from flask import Flask, request, jsonify
from flask_cors import CORS
from experta import *

app = Flask(__name__)
CORS(app)

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
        self.warnings = set()
        self.recommendations = set()

    def add_warning(self, message):
        """Store warning messages"""
        self.warnings.add(message)

    def add_recommendation(self, message):
        """Store recommendation messages"""
        self.recommendations.add(message)

    # 🚨 CRITICAL WARNINGS (Highest Priority)
    @Rule(WaterQuality(temperature=P(lambda t: t > 35), dissolved_oxygen=P(lambda o: o < 3)), salience=10)
    def extreme_heat_danger(self):
        self.add_warning("🔥 Extreme heat detected! Fish may be gasping due to oxygen depletion.")
        self.add_recommendation("Increase aeration and provide shade. Consider a partial water exchange.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 3)), salience=10)
    def critical_low_oxygen(self):
        self.add_warning("⚠️ Critically low oxygen levels! Fish may be lethargic or surfacing.")
        self.add_recommendation("Immediately activate aerators or increase water circulation.")

    @Rule(WaterQuality(ammonia=P(lambda a: a > 1)), salience=10)
    def severe_ammonia_toxicity(self):
        self.add_warning("☠️ High ammonia toxicity! Fish gills may be inflamed or discolored.")
        self.add_recommendation("Perform a 30-50% water change and reduce feeding to limit waste buildup.")

    # ⚠️ MODERATE WARNINGS (Medium Priority)
    @Rule(WaterQuality(temperature=P(lambda t: t > 30), dissolved_oxygen=P(lambda o: o < 4)), salience=5)
    def critical_oxygen_drop(self):
        self.add_warning("🌡️ High temperature + low oxygen detected! Fish stress is increasing.")
        self.add_recommendation("Increase aeration and monitor fish behavior for signs of distress.")

    @Rule(WaterQuality(salinity=P(lambda s: s > 40)), salience=5)
    def high_salinity_risk(self):
        self.add_warning("🧂 Elevated salinity! Freshwater species may experience stress.")
        self.add_recommendation("Gradually dilute with freshwater to restore balance.")

    @Rule(WaterQuality(ammonia=P(lambda a: a > 0.5), dissolved_oxygen=P(lambda o: o < 4)), salience=5)
    def ammonia_stress_oxygen_drop(self):
        self.add_warning("⚠️ Ammonia buildup and low oxygen detected! Fish are at risk of suffocation.")
        self.add_recommendation("Increase aeration, reduce feeding, and perform a partial water change.")

    @Rule(WaterQuality(time_of_day="night", dissolved_oxygen=P(lambda o: o < 5)), salience=5)
    def night_oxygen_depletion(self):
        self.add_warning("🌙 Oxygen levels dropping at night! Algae respiration may be consuming oxygen.")
        self.add_recommendation("Ensure aerators run at night to maintain stable oxygen levels.")

    # ℹ️ LOW-PRIORITY WARNINGS (Mild Concerns)
    @Rule(WaterQuality(temperature=P(lambda t: t < 15)), salience=1)
    def low_temp_slow_metabolism(self):
        self.add_warning("🥶 Cold water detected! Fish metabolism slows down in low temperatures.")
        self.add_recommendation("Adjust feeding schedule and avoid sudden temperature fluctuations.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 5)), salience=1)
    def low_oxygen_warning(self):
        self.add_warning("📉 Oxygen is lower than ideal. Fish may experience mild stress.")
        self.add_recommendation("Increase aeration, especially during warm periods.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o > 10)), salience=1)
    def high_oxygen_saturation(self):
        self.add_warning("💨 Excess oxygen detected! Risk of gas bubble disease.")
        self.add_recommendation("Reduce aeration slightly if fish show abnormal buoyancy.")

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

    return jsonify({
        "warnings": list(engine.warnings) if engine.warnings else ["No critical issues detected."],
        "recommendations": list(engine.recommendations) if engine.recommendations else ["No immediate action needed."]
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
