# OptiPlex 3080 Relay Setup Checklist (Windows)

Use this exact checklist on your OptiPlex.

## Known machine/network facts

- IPv4: `192.168.50.168`
- Gateway: `192.168.50.1`
- DNS: `192.168.50.1`
- MAC: `70:B5:E8:6C:30:4D`
- Link speed: `1000/1000 Mbps`

## 1) Network and power prerequisites

- [ ] Router DHCP reservation confirmed for MAC `70:B5:E8:6C:30:4D` -> `192.168.50.168`
- [ ] OptiPlex power profile set to never sleep
- [ ] NIC power saving disabled
- [ ] Windows update/restart outside business hours

## 2) Install relay app

- [ ] Open folder `relay/`
- [ ] Double-click [`start_relay.bat`](relay/start_relay.bat)
- [ ] Wait for installer steps (Python detect/install, dependencies, self-test)
- [ ] Confirm browser opens at `http://127.0.0.1:8787`
- [ ] If script shows error, read message and rerun after fix

## 3) Configure from setup UI

Go to `System Setup` and fill:

- [ ] Frappe Base URL (your cloud site URL)
- [ ] API Key
- [ ] API Secret
- [ ] Relay Host: `0.0.0.0`
- [ ] Relay Port: `8787` (or your chosen fixed port)
- [ ] Allowed Subnet: `192.168.50.0/24`
- [ ] Save Configuration

## 4) One-click bootstrap (Windows)

- [ ] Click `Run Windows Bootstrap`
- [ ] Confirm firewall rule was added
- [ ] Confirm startup task was created

## 5) Queue monitoring

- [ ] Open Dashboard (`/`)
- [ ] Open Queue (`/queue`)
- [ ] Verify real-time refresh updates counters

## 7) Simple run instructions (daily)

- [ ] To start relay: double-click [`start_relay.bat`](relay/start_relay.bat)
- [ ] To check status: open `http://127.0.0.1:8787/health`
- [ ] To view queue live: open `http://127.0.0.1:8787/queue`

## 6) POS integration usage

- [ ] POS clients target relay using `http://192.168.50.168:8787`
- [ ] Keep feature enabled only for selected POS Profile
- [ ] Keep all other POS Profiles unchanged

