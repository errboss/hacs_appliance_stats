# Appliance Stats

Current package version in this bundle: 0.2.5

Malá custom integrace pro Home Assistant, která z výkonu chytré zásuvky odvozuje aktivitu spotřebiče a základní statistiky jako počet běhů, dobu běhu a spotřebu energie.

## Co vytváří

Pro každý přidaný spotřebič vytvoří:

- `binary_sensor.<spotrebic>_active`
- `sensor.<spotrebic>_runtime_total`
- `sensor.<spotrebic>_energy_active_total`
- `sensor.<spotrebic>_runs_total`

## Jak se nově počítá energie a běhy

Integrace teď používá **dvě vstupní entity**:
- **power sensor** – slouží jen k rozhodnutí, zda je spotřebič aktivní
- **energy sensor** – z této vybrané entity se bere spotřeba

To znamená:
- aktivita se dál vyhodnocuje z výkonu podle `power_threshold`, `delay_on` a `delay_off`
- do `energy_active_total` se započítává jen ta část přírůstku, která vznikla v době, kdy byl spotřebič vyhodnocen jako aktivní
- `runs_total` se zvýší při dokončení běhu, tedy při přechodu z aktivního do neaktivního stavu

Doporučení: jako `energy` entitu vybírej kumulativní senzor typu `total_increasing` z chytré zásuvky nebo elektroměru.

## Instalace

### Varianta A – ručně

1. Zkopírujte složku `custom_components/appliance_stats` do vaší HA konfigurace.
2. Restartujte Home Assistant.
3. Otevřete **Settings → Devices & Services → Add Integration**.
4. Vyhledejte **Appliance Stats**.
5. Vyplňte:
   - název spotřebiče
   - entitu výkonu, např. `sensor.playstation_power`
   - entitu energie, např. `sensor.playstation_energy`
   - práh ve W, od kterého se má zařízení počítat jako aktivní
   - `delay_on` a `delay_off`

### Varianta B – HACS custom repository

1. Nahrajte tento repozitář na GitHub.
2. Přidejte ho v HACS jako **custom repository / Integration**.
3. Nainstalujte a restartujte Home Assistant.
4. Přidejte integraci přes UI.

## Doporučené nastavení

### PlayStation

- threshold: `10`
- delay_on: `30`
- delay_off: `120`
- update_interval: `30`

### Kávovar

- threshold: `30`
- delay_on: `5`
- delay_off: `60`
- update_interval: `15`

## Příklad pro `utility_meter`

Z total senzorů si můžeš v HA odvodit denní nebo měsíční statistiky mimo integraci:

```yaml
utility_meter:
  playstation_runtime_daily:
    source: sensor.playstation_runtime_total
    cycle: daily

  playstation_energy_daily:
    source: sensor.playstation_energy_active_total
    cycle: daily
```

## Aktuální stav na jedné kartě

```yaml
type: entities
title: PlayStation
entities:
  - binary_sensor.playstation_active
  - sensor.playstation_runtime_total
  - sensor.playstation_energy_active_total
  - sensor.playstation_runs_total
```

## Poznámky

- Integrace sleduje jednu zásuvku na jeden config entry. Přidej ji opakovaně pro více zařízení.
- `runtime_total`, `energy_active_total` a `runs_total` jsou kumulativní hodnoty vhodné pro dlouhodobé statistiky.
- Přesnost běhového času závisí na kvalitě a frekvenci aktualizace zdrojového senzoru výkonu.
- Přesnost energie závisí na tom, jak často se aktualizuje vybraná `energy` entita.
- Pokud `energy` senzor resetuje hodnotu nebo jde zpět, záporný skok se ignoruje a měření pokračuje od nové hodnoty.
- Source i energy entity se vybírají přes **entity selector** z UI seznamu.
