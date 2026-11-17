import pandas as pd
from sqlalchemy import create_engine, text
from getpass import getuser

engine = create_engine(
    f"postgresql+psycopg://{getuser()}:secret1@localhost/sncf_c_gro_nul"
)

requete = """
SELECT COUNT(*) AS total
FROM regularite_tgv;
"""

with engine.connect() as conn:
    df = pd.read_sql(text(requete), conn)


if df["total"].iloc[0] == 12907:
    print("Test ok, nombre de ligne: ", df["total"].iloc[0])
else: 
    print("Test invalide, vérifier que la bonne base de donné a été installé, nombre de ligne actuel: ", df["total"].iloc[0])


