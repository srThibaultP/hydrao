# Hydrao — Custom Component Home Assistant

Intégration Home Assistant **sans gateway externe** pour les pommeaux de douche connectés **Hydrao** (Aloe, Cereus, Yucca, First).

La communication BLE est gérée directement par HA via son subsystem Bluetooth natif — **aucun Raspberry Pi, aucun service tiers requis**.

## Prérequis

- Home Assistant ≥ 2024.1 avec le subsystem **Bluetooth** activé
- Un adaptateur Bluetooth sur la machine qui fait tourner HA (Raspberry Pi 4/5, NUC, etc.)
- Le pommeau Hydrao à portée BLE

## Installation

### Via HACS (recommandé)

1. HACS → ⋮ → **Dépôts personnalisés** → coller l'URL du repo → catégorie **Intégration**
2. Installer **Hydrao Shower Head**
3. Redémarrer Home Assistant

### Manuelle

```
cp -r custom_components/hydrao  <config_dir>/custom_components/hydrao
```
Redémarrer Home Assistant.

## Configuration

**Option A — Découverte automatique (recommandée)**

Si le pommeau est à portée, HA détecte automatiquement le BLE advertisement `HYDRAO_SHOWER*` et propose une notification dans **Paramètres → Appareils et Services**.

**Option B — Ajout manuel**

1. **Paramètres → Appareils et Services → + Ajouter une intégration**
2. Chercher **Hydrao**
3. Sélectionner l'appareil dans la liste ou saisir l'adresse MAC Bluetooth

## Entités créées (par pommeau)

| Entité | Type | Description |
|--------|------|-------------|
| `sensor.live_volume` | Sensor | Volume en cours (L) |
| `sensor.live_flow` | Sensor | Débit instantané (L/min) |
| `sensor.live_temperature` | Sensor | Température eau en cours (°C) |
| `sensor.live_duration` | Sensor | Durée douche en cours (s) |
| `sensor.last_shower_volume` | Sensor | Volume dernière douche (L) |
| `sensor.last_shower_temperature` | Sensor | Température dernière douche (°C) |
| `sensor.last_shower_flow` | Sensor | Débit moyen dernière douche (L/min) |
| `sensor.last_shower_duration` | Sensor | Durée dernière douche (s) |
| `sensor.last_shower_soaping_time` | Sensor | Temps savonnage (s) |
| `sensor.last_shower_date` | Sensor | Horodatage dernière douche |
| `binary_sensor.is_showering` | Binary Sensor | Douche en cours (ON/OFF) |
| `sensor.rssi` *(désactivé)* | Sensor | Signal BLE (dBm) |
| `sensor.firmware_version` *(désactivé)* | Sensor | Version firmware |

## Architecture

```
Pommeau Hydrao (BLE)
       ↕ GATT (bleak + bleak-retry-connector)
Home Assistant — custom_components/hydrao
  ├── protocol.py      ← décodage binaire GATT (porté de hydrao-ble-raspberry)
  ├── ble_client.py    ← connexion, sync historique, polling live (2s)
  ├── coordinator.py   ← push callbacks → entités HA
  ├── config_flow.py   ← découverte passive + saisie manuelle
  ├── sensor.py        ← 12 capteurs
  └── binary_sensor.py ← douche en cours
```

## Protocole BLE

Basé sur le code open source [hydrao-ble-raspberry](https://github.com/hydrao-opensource/hydrao-ble-raspberry) (Apache 2.0).

UUIDs GATT utilisés :

| Caracteristique | UUID |
|-----------------|------|
| UUID appareil   | `0000ca28-…` |
| Firmware        | `00002a26-…` |
| Hardware        | `0000ca24-…` |
| Volume live     | `0000ca1c-…` |
| Débit live      | `0000ca31-…` |
| Température live| `0000ca32-…` |
| Seuils LED      | `0000ca1d-…` |
| Calibration     | `0000ca30-…` |
| Plage douches   | `0000ca21-…` |
| Requête douche  | `0000ca22-…` |
| Données douche  | `0000ca23-…` |

## Licence

Apache 2.0 — basé sur les projets open source [Hydrao](https://github.com/hydrao-opensource).
