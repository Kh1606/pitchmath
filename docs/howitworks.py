"""Render the PitchMath 'how it works' flowchart.

Run from this directory:  python howitworks.py
Deps:  pip install diagrams cairosvg   (and Graphviz on PATH)
"""
import os
from diagrams import Diagram, Cluster, Edge
from diagrams.generic.storage import Storage
from diagrams.custom import Custom

ICONS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "_diagram_icons"))


def icon(name: str) -> str:
    return os.path.join(ICONS, f"{name}.png")


graph_attr = {"fontsize": "18", "bgcolor": "white", "pad": "0.4", "splines": "spline"}
node_attr = {"fontsize": "13"}
edge_attr = {"fontsize": "11"}

with Diagram(
    "PitchMath — football analytics platform",
    filename="howitworks",
    direction="LR",
    show=False,
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    api = Storage("API-Football")

    with Cluster("Extractor"):
        configs = Custom("YAML configs\nper competition\n(EPL · UCL · K League…)", icon("files"))
        extractor = Custom("Python extractor\nfixtures · team · player stats", icon("python"))
        configs >> Edge(color="#888888", style="dashed") >> extractor

    db = Custom("Postgres\n(or SQLite)\nDocker compose", icon("postgresql"))
    app = Custom("Streamlit app\nMatch · Team · Player\n+ Team DNA radar", icon("streamlit"))

    api >> Edge(color="#0ea5e9", label="fetch") >> extractor
    extractor >> Edge(color="#10b981", label="upsert") >> db
    db >> Edge(color="#f59e0b", label="read") >> app
