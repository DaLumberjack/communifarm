# Onboarding

1. Install Communifarm under `custom_components/communifarm`.
2. Restart Home Assistant. Use **Metric** (Celsius, kilograms) under Settings → System → General. Communifarm follows that setting. A United States country still starts in Fahrenheit unless you change it. The scratch setup test selects Metric for you.
3. Settings → Devices & services → Add integration → Communifarm.
4. Create Site and Environment names.
5. Accept or change temperature, humidity, fan, and switch bindings.
6. Set temperature/humidity targets and a starter batch name.
7. Finish — Communifarm entities and a managed dashboard model are created.
8. Open **Communifarm** in the sidebar to see Current settings and adjust Targets there (see [dashboard.md](dashboard.md)).
9. Climate rooms are seeded at setup, including the sensors and machines drawn on the layout (see [climate.md](climate.md)).

No `configuration.yaml` edits are required for the normal path.
