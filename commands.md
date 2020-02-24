Commands for extracting data by collection area:

```
python3 run.py -query "coll_id=1" -name "NorthAmerica"
python3 run.py -query "coll_id=2" -name "Africa"
python3 run.py -query "coll_id=3" -name "Asia"
python3 run.py -query "coll_id=4" -name "MexicoAndCentralAmerica"
python3 run.py -query "coll_id=5" -name "SouthAmerica"
python3 run.py -query "coll_id=6" -name "Pacific"
python3 run.py -query "coll_id=7" -name "Europe"
```

And downloading images:

```
python3 download_images.py -in "data/NorthAmerica.csv" -out "images/NorthAmerica/"
python3 download_images.py -in "data/Africa.csv" -out "images/Africa/"
python3 download_images.py -in "data/Asia.csv" -out "images/Asia/"
python3 download_images.py -in "data/MexicoAndCentralAmerica.csv" -out "images/MexicoAndCentralAmerica/"
python3 download_images.py -in "data/SouthAmerica.csv" -out "images/SouthAmerica/"
python3 download_images.py -in "data/Pacific.csv" -out "images/Pacific/"
python3 download_images.py -in "data/Europe.csv" -out "images/Europe/"
```
