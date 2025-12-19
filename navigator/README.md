# Navigator App logic

This app loads `/ontology/nepal-marriage-ontology.ttl` and visualizes the structure.

## Setup
1. Ensure `rdflib` is installed: `pip install rdflib` (Already done).
2. The app `navigator` is added to `INSTALLED_APPS`.
3. URLs are hooked up.

## Running
Run the server:
```bash
python manage.py runserver
```

Then visit `http://127.0.0.1:8000/`.

## Features
- **Tree View**: Hierarchical view of rituals based on `crm:P10_falls_within`.
- **Details**: Clicking a node shows all RDF properties derived from the Turtle file.
- **Glassmorphism UI**: A modern, dark-themed interface.
