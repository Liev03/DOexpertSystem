from flask import Flask, request, jsonify
from flask_cors import CORS
from experta import KnowledgeEngine, Rule, Fact, P

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

class OxygenPredictor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.most_critical_warning = None
        self.most_critical_recommendation = None
        self.highest_priority = -1  # Track highest priority rule triggered

    def add_warning(self, message, priority):
        if priority > self.highest_priority:
            self.most_critical_warning = message
            self.highest_priority = priority  # Update priority

    def add_recommendation(self, message, priority):
        if priority >= self.highest_priority:  # Ensure matching recommendation
            self.most_critical_recommendation = message

    # === Oxygen Rules ===
    @Rule(Fact(dissolved_oxygen=P(lambda x: x < 3)))
    def critically_low_oxygen(self):
        self.add_warning("⚠️ Critically low oxygen levels! Fish may be lethargic or surfacing.", priority=3)
        self.add_recommendation("Immediately activate aerators or increase water circulation.", priority=3)

    @Rule(Fact(dissolved_oxygen=P(lambda x: 3 <= x < 5)))
    def low_oxygen(self):
        self.add_warning("📉 Oxygen is lower than ideal. Fish may experience mild stress.", priority=2)
        self.add_recommendation("Increase aeration, especially during warm periods.", priority=2)

    @Rule(Fact(dissolved_oxygen=P(lambda x: x > 8)))
    def excessive_oxygen(self):
        self.add_warning("🌊 Excessive dissolved oxygen detected! Potential gas bubble disease risk.", priority=1)
        self.add_recommendation("Reduce aeration and monitor fish closely.", priority=1)

    # === Temperature Rules ===
    @Rule(Fact(temperature=P(lambda x: x < 20)))
    def cold_water(self):
        self.add_warning("❄️ Cold water detected! Fish metabolism slows down in low temperatures.", priority=1)
        self.add_recommendation("Adjust feeding schedule and avoid sudden temperature fluctuations.", priority=1)

    @Rule(Fact(temperature=P(lambda x: x > 30)))
    def high_temperature(self):
        self.add_warning("🔥 High water temperature detected! Oxygen levels may drop.", priority=2)
        self.add_recommendation("Increase aeration and monitor fish behavior closely.", priority=2)

    # === Ammonia Rules ===
    @Rule(Fact(ammonia=P(lambda x: x > 0.5)))
    def high_ammonia(self):
        self.add_warning("☠️ High ammonia levels detected! Fish health is at risk.", priority=3)
        self.add_recommendation("Perform partial water changes and check filtration systems.", priority=3)

    # === pH Rules ===
    @Rule(Fact(pH=P(lambda x: x < 6)))
    def low_pH(self):
        self.add_warning("🔴 Low pH detected! Water is too acidic.", priority=2)
        self.add_recommendation("Add buffering agents like crushed coral or baking soda.", priority=2)

    @Rule(Fact(pH=P(lambda x: x > 8.5)))
    def high_pH(self):
        self.add_warning("🟢 High pH detected! Water is too alkaline.", priority=2)
        self.add_recommendation("Use pH-lowering treatments like peat moss or driftwood.", priority=2)

    # === Salinity Rules ===
    @Rule(Fact(salinity=P(lambda x: x > 10)))  # Adjust based on your ideal range
    def high_salinity(self):
        self.add_warning("⚠️ High salinity detected! Water may not be suitable for freshwater species.", priority=1)
        self.add_recommendation("Dilute with fresh water to lower salinity.", priority=1)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    predictor = OxygenPredictor()
    predictor.reset()
    predictor.declare(Fact(**data))
    predictor.run()

    result = {
        "warnings": [predictor.most_critical_warning] if predictor.most_critical_warning else [],
        "recommendations": [predictor.most_critical_recommendation] if predictor.most_critical_recommendation else []
    }
    return jsonify(result)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
