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
    time_of_day = Field(str)

class OxygenPredictor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.warning = None  # Store only one warning
        self.recommendation = None  # Store only one recommendation

    def add_warning(self, message):
        if self.warning is None:  # Only store the most urgent warning
            self.warning = message

    def add_recommendation(self, message):
        if self.recommendation is None:  # Only store the most relevant recommendation
            self.recommendation = message

    # 🚨 CRITICAL WARNINGS (Highest Priority)
    @Rule(WaterQuality(temperature=P(lambda t: t > 35), dissolved_oxygen=P(lambda o: o < 3)), salience=10)
    def extreme_heat_danger(self):
        self.add_warning("🔥 Extreme heat! Fish may be gasping at the surface due to oxygen depletion.")
        self.add_recommendation("Increase aeration, lower water temperature (e.g., shading or water exchange).")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 3)), salience=10)
    def critical_low_oxygen(self):
        self.add_warning("⚠️ Oxygen critically low! Fish may be lethargic or floating near the surface.")
        self.add_recommendation("Immediately turn on aerators or increase water circulation.")

    @Rule(WaterQuality(ammonia=P(lambda a: a > 1)), salience=10)
    def severe_ammonia_toxicity(self):
        self.add_warning("☠️ Dangerous ammonia levels! Fish gills may appear red or inflamed.")
        self.add_recommendation("Perform a 30-50% water change and check for overfeeding or excess waste.")

    # ⚠️ MODERATE WARNINGS (Medium Priority)
    @Rule(WaterQuality(temperature=P(lambda t: t > 30), dissolved_oxygen=P(lambda o: o < 4)), salience=5)
    def critical_oxygen_drop(self):
        self.add_warning("🌡️ High temperature + low oxygen! Fish stress levels rising.")
        self.add_recommendation("Increase aeration and monitor fish activity closely.")

    @Rule(WaterQuality(salinity=P(lambda s: s > 40)), salience=5)
    def high_salinity_risk(self):
        self.add_warning("🧂 High salinity detected! Some freshwater species may be struggling.")
        self.add_recommendation("Gradually dilute with fresh water to reduce stress.")

    @Rule(WaterQuality(ammonia=P(lambda a: a > 0.5), dissolved_oxygen=P(lambda o: o < 4)), salience=5)
    def ammonia_stress_oxygen_drop(self):
        self.add_warning("⚠️ Ammonia + low oxygen! Fish are at risk of suffocation.")
        self.add_recommendation("Reduce feeding, add aeration, and perform a partial water change.")

    @Rule(WaterQuality(time_of_day="night", dissolved_oxygen=P(lambda o: o < 5)), salience=5)
    def night_oxygen_depletion(self):
        self.add_warning("🌙 Oxygen dropping at night! Algae may be consuming oxygen.")
        self.add_recommendation("Run aerators overnight to maintain oxygen levels.")

    # ℹ️ LOW-PRIORITY WARNINGS (Mild Concerns)
    @Rule(WaterQuality(temperature=P(lambda t: t < 15)), salience=1)
    def low_temp_slow_metabolism(self):
        self.add_warning("🥶 Water too cold! Fish metabolism is slowing down.")
        self.add_recommendation("Adjust feeding schedule and avoid sudden temperature changes.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o < 5)), salience=1)
    def low_oxygen_warning(self):
        self.add_warning("📉 Oxygen is lower than ideal. Monitor fish closely.")
        self.add_recommendation("Increase aeration, especially during warmer hours.")

    @Rule(WaterQuality(dissolved_oxygen=P(lambda o: o > 10)), salience=1)
    def high_oxygen_saturation(self):
        self.add_warning("💨 Too much oxygen! Risk of gas bubble disease.")
        self.add_recommendation("Reduce aeration if fish show abnormal buoyancy.")

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

    engine = OxygenPredictor()
    engine.reset()
    engine.declare(WaterQuality(**processed_data))
    engine.run()

    return jsonify({
        "warning": engine.warning if engine.warning else "✅ No critical issues detected.",
        "recommendation": engine.recommendation if engine.recommendation else "✅ No action needed."
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
