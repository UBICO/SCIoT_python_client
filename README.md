# SCIoT project
*Copy of the SCIoT  project to work on the python clients*

Questa è una copia del progetto per testare l'implementazione dei client Python.

## 05/11/2025

### Updates:
- Commentate le configurazione MQTT e WebSocket dal file settings.yaml in modo da eseguire solo la versione http. Non è quindi necessario fare il punto 2 della guida a come lanciare (premere `CTRL + C`) all'avvio. 
- Aggiunta la cartella 'simulated_results' contenente lo script 'simulated_scenario.py' utilizzato per creare i file .csv dei risultati simulati.
- il best offloading layer viene scelto correttamente, non più in modo randomico. 

### Punti da risolvere:
- Quando viene fatto l'offloading su certi layer va in errore. Credo che il problema sia dovuto al fatto che per alcuni layer l'edge si aspetta di ricevere un numero di pesi differente. 

### Altre indicazioni: 
- Per intervenire su la latency: message_data.py → get_latency()
- Per intervenire su edge inference time: models/model_manager.py → wrapper()



## 13/07/2025

Creato lo script `server_client_light/client/http_client.py` (clone del codice per ESP32)

### Punti da risolvere
- Attualmente il best offloading layer viene scelto in modo random per simulare condizioni in cui le performance della rete degradano → **capire come fare.**
- Inserire codice su server per **salvare su file i tempi di inferenza**

### Come lanciare

1. Seguire le istruzioni scritte da Mattia per l'avvio del server (eventualmente inserire `tensorflow` per macOS nel file `config`)
2. All'avvio di `run_edge.py`, premere `CTRL + C` per terminare la modalità websocket e far partire la modalità HTTP
3. Avviare il client:

   ```sh
   python server_client_light/client/http_client.py
   ```

===========================================================================================================================================

The Split Computing on IoT (SCIoT) project provides tools to use Edge Impulse models in ESP32 devices, using split computing techniques.

![Unit Tests](https://github.com/UBICO/SCIoT/actions/workflows/codecov.yml/badge.svg) [![Coverage](https://codecov.io/github/UBICO/SCIoT//coverage.svg?branch=main)](https://codecov.io/gh/UBICO/SCIoT) [![Powered by UBICO](https://img.shields.io/badge/powered%20by-UBICO-orange.svg?style=flat&colorA=E1523D&colorB=007D8A)]()  

## Publications
If you use this work, please consider citing our work:
- F. Bove, S. Colli and L. Bedogni, "Performance Evaluation of Split Computing with TinyML on IoT Devices," 2024 IEEE 21st Consumer Communications & Networking Conference (CCNC), Las Vegas, NV, USA, 2024, pp. 1-6, [DOI Link](http://dx.doi.org/10.1109/CCNC51664.2024.10454775).
- F. Bove and L. Bedogni, "Smart Split: Leveraging TinyML and Split Computing for Efficient Edge AI," 2024 IEEE/ACM Symposium on Edge Computing (SEC), Rome, Italy, 2024, pp. 456-460, [DOI Link](http://dx.doi.org/10.1109/SEC62691.2024.00052).

## Configuration
Clone the repository and navigate into it:

```sh
git clone https://github.com/UBICO/SCIoT.git
cd SCIoT
```

Create the virtual environment and install the dependencies:

```sh
uv sync
```

Activate the virtual environment:

```sh
source .venv/bin/activate
```

### Model setup
- Save your keras model as `test_model.h5` in `src/server/models/test/test_model/`
- Save your test image as `test_image.png` in `src/server/models/test/test_model/pred_data/`
- Split the model by running `python3 model_split.py` from `src/server/models/`
- Configure the paths as needed using `src/server/commons.py`

### Server setup
- Configure the server using `src/server/settings.yaml`

## Usage
From the repository's root directory, activate the virtual environment:

```sh
source .venv/bin/activate
```

Start the MQTT broker:

```sh
docker compose up
```

Run the edge server:

```sh
python3 src/server/edge/run_edge.py
```

Run the analytics dashboard:

```sh
streamlit run src/server/web/webpage.py
```
