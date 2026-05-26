# MetaRen - Update Postgres DB (fixtures + new finished match stats)
Set-Location $PSScriptRoot

# ensure .env is loaded by python-dotenv inside scripts
python -m extractors.run `
  --config `
    configs/country/england/epl.yml `
    configs/country/spain/laliga.yml `
    configs/country/italy/serie_a.yml `
    configs/country/germany/bundesliga.yml `
    configs/country/france/ligue11.yml `
  --update-only `
  --db pg
