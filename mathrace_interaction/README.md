# Turing @ DMF: interaction with mathrace

`mathrace_interaction` contains several utilities to have `mathrace` and `turing` interacting. [Docker containers](docker/README.md) come with `mathrace_interaction` already installed.

## Journal information

### List all supported journal version

The journal format evolved over time. `mathrace_interaction/list_journal_versions.py` lists all versions currently supported by `mathrace_interaction`.

**Example 1**: list all supported versions with
```
python3 -m mathrace_interaction.list_journal_versions
```

### Determine version of a specific journal version

Provide an input journal to `mathrace_interaction/determine_journal_version.py` to determine its version.

**Example 1**: determine version of a journal in the `data` folder with
```
python3 -m mathrace_interaction.determine_journal_version -i data/2013/disfida.journal
```

## Static journal conversion

### Convert from `mathrace` to `turing`

Provide an input journal to `mathrace_interaction/journal_reader.py` to convert it to the `turing` format.

**Example 1**: convert a journal in the `data` folder into a JSON file with
```
python3 -m mathrace_interaction.journal_reader -i data/2013/disfida.journal -n "Disfida 2013" -d "2013-03-08T15:14:16+01:00" -o /tmp/turing-dict.json
```
The resulting JSON file can be modified locally, or uploaded to a running `turing` instance.

**Example 2**: upload a journal in the `data` folder to a running `turing` instance with
```
TURING_RACE_PRIMARY_KEY=$(python3 -m mathrace_interaction.journal_reader -i data/2013/disfida.journal -n "Disfida 2013" -d "2013-03-08T15:14:16+01:00" -u)
echo ${TURING_RACE_PRIMARY_KEY}
```
The output reports the primary key of the uploaded race, which will be available on `turing` in the list of past races.

**Example 3**: convert the race setup of a journal in the `data` folder into a JSON file with
```
python3 -m mathrace_interaction.journal_reader -i data/2013/disfida.journal -n "Disfida 2013 (race setup only)" -s -o /tmp/turing-dict-setup-only.json
```
The resulting JSON file will contain the same race setup (parameters, teams) as the input journal file, but the race will contain no events. The JSON file can be then uploaded to a running `turing` instance, and the race started from there.

**Example 4**: upload the race setup of a journal in the `data` folder to a running `turing` instance with
```
TURING_RACE_SETUP_ONLY_PRIMARY_KEY=$(python3 -m mathrace_interaction.journal_reader -i data/2013/disfida.journal -n "Disfida 2013 (race setup only)" -s -u)
echo ${TURING_RACE_SETUP_ONLY_PRIMARY_KEY}
```
Same as Example 3, except that it uploads to `turing`. The converted race will be available on `turing` in the list of past races. The uploaded race will be available on `turing` in the list of races to be started.

### Convert from `turing` to `mathrace`

Provide an input `turing` race to `mathrace_interaction/journal_writer.py` to convert it to the journal format.

**Preliminaries**: since the `data` folder does not ship any JSON file, the examples below assumes that all scripts in the previous section have been already run.

**Example 1**: convert a JSON file into a journal
```
python3 -m mathrace_interaction.journal_writer -i /tmp/turing-dict.json -v r25013 -o /tmp/mathrace.journal
python3 -m mathrace_interaction.journal_writer -i /tmp/turing-dict-setup-only -v r25013 -o /tmp/mathrace-setup-only.journal
```

**Example 2**: download a race from a running `turing` instance and store into a journal with
```
python3 -m mathrace_interaction.journal_writer -d ${TURING_RACE_PRIMARY_KEY} -v r25013 -o /tmp/mathrace.journal
python3 -m mathrace_interaction.journal_writer -d ${TURING_RACE_SETUP_ONLY_PRIMARY_KEY} -v r25013 -o /tmp/mathrace-setup-only.journal
```

### Convert from `mathrace` to `mathrace`, different journal versions

Provide an input journal and a version to `mathrace_interaction/journal_version_converter.py` to convert the provided journal to an equivalent one based on the target version.

**Example 1**: convert a journal in the `data` folder to an equivalent journal of a different version with
```
python3 -m mathrace_interaction.journal_version_converter -i data/2013/disfida.journal -v r25013 -o /tmp/mathrace-r25013.journal
```

## Static journal filtering

### Filter events up to a specific one

Provide an input journal and an event protocol to `mathrace_interaction/filter/journal_event_filterer_by_id.py` to obtain an equivalent journal at the time of the provided event.

**Example 1**: starting from a journal in the `data` folder, create an equivalent journal that contains all events before (or including) the 100th event with
```
python3 -m mathrace_interaction.filter.journal_event_filterer_by_id -i data/2015/disfida.journal -p 100 -o /tmp/mathrace-filtered-by-id.journal
```

### Filter events up to a specific time

Provide an input journal and a timestamp to `mathrace_interaction/filter/journal_event_filterer_by_timestamp.py` to obtain an equivalent journal at the provided time.

**Example 1**: starting from a journal in the `data` folder, create an equivalent journal that contains all events that happened in the first 10 minutes with
```
python3 -m mathrace_interaction.filter.journal_event_filterer_by_timestamp -i data/2013/disfida.journal -t 600 -o /tmp/mathrace-filtered-by-time-2013.journal
python3 -m mathrace_interaction.filter.journal_event_filterer_by_timestamp -i data/2023/disfida_new_format.journal -t "00:10:00" -o /tmp/mathrace-filtered-by-time-2023.journal
```

## Live `mathrace` journal to live `turing`

The script `mathrace_interaction/live_journal_to_live_turing.py` transfers race events from a live `mathrace` session to a live `turing` one.

### Before the race

#### Step 1: have a journal file with the race setup

```
LIVE_JOURNAL_RACE_SETUP="data/2013/disfida.journal"
LIVE_RACE_NAME="Disfida 2013 (mock live race)"
```

#### Step 2: upload the race setup to turing

```
LIVE_TURING_PRIMARY_KEY=$(python3 -m mathrace_interaction.journal_reader -i "${LIVE_JOURNAL_RACE_SETUP}" -n "${LIVE_RACE_NAME}" -s -u)
echo ${LIVE_TURING_PRIMARY_KEY}
```
Make a note of the value of `${LIVE_TURING_PRIMARY_KEY}`.

#### Step 3: mark yourself as administrator of the uploaded race

Go to `http://turing-host/admin/engine/gara/${LIVE_TURING_PRIMARY_KEY}/change/` and set your user as administrator of the uploaded race, otherwise on race day it will not have the permission to start the race from the web interface.

### At the beginning of the race

#### Step 1: determine where `mathrace` will write the journal file

```
LIVE_JOURNAL_FILE="/var/tmp/journal.log"
LIVE_JOURNAL_HOST=""  # or the name of a SSH host
LIVE_JOURNAL_HOST_USER=""  # or the name of a user who can connect via SSH to ${LIVE_JOURNAL_HOST} without typing any password
```

#### Step 2: start the race on `mathrace` and on `turing`

- `mathrace` will be the main race server, and will start the race with
```
./utils/attendi_inizio_gara.sh --tra 1  # race start in 1 minute
```
- Simultaneously, go to the `turing` web interface and start race `${LIVE_TURING_PRIMARY_KEY}`.

#### Step 3: send live updates from `mathrace` to `turing`

```
python3 -m mathrace_interaction.live_journal_to_live_turing -i "${LIVE_JOURNAL_FILE}" -h "${LIVE_JOURNAL_HOST}" -u "${LIVE_JOURNAL_HOST_USER}" -t "${LIVE_TURING_PRIMARY_KEY}" -s 10 -o "/shared/host-tmp/live_${LIVE_TURING_PRIMARY_KEY}"
```

## Live `turing` to live `mathrace` journal

The script `mathrace_interaction/live_turing_to_live_journal.py` transfers race events from a live `turing` session to a live `mathrace` journal.

### Before the race

Set up the race through the turing web interface, and make a note of the value of the race id as `${LIVE_TURING_PRIMARY_KEY}`.

### At the beginning of the race

#### Step 1: send live updates from `turing`

```
python3 -m mathrace_interaction.live_turing_to_live_journal -t "${LIVE_TURING_PRIMARY_KEY}" -s 10 -v r25013 -o "/shared/host-tmp/live_${LIVE_TURING_PRIMARY_KEY}"
```

#### Step 2: sync from docker host to another machine

```
while true; do
    rsync -arvz ${TURING_HOST_USER}@${TURING_HOST}:/tmp/shared-turing-dmf/live_${LIVE_TURING_PRIMARY_KEY}/ /tmp/live_${LIVE_TURING_PRIMARY_KEY}
    sleep 5
done
```

## Live `turing` to HTML output

The script `mathrace_interaction/live_turing_to_html.py` transfers race events from a live `turing` session to a sequence of HTML files, which are suitable to update a mirror website.

### Before the race

Set up the race through the turing web interface, and make a note of the value of the race id as `${LIVE_TURING_PRIMARY_KEY}`.

### At the beginning of the race

#### Step 1: send live updates from `turing`

```
python3 -m mathrace_interaction.live_turing_to_html -u "http://0.0.0.0" -p $(cat /mnt/secrets/.django_superuser_initial_password) -t "${LIVE_TURING_PRIMARY_KEY}" -s 10 -o "/shared/host-tmp/live_${LIVE_TURING_PRIMARY_KEY}"
```

#### Step 2: sync from docker host to another machine

```
while true; do
    rsync -arvz ${TURING_HOST_USER}@${TURING_HOST}:/tmp/shared-turing-dmf/live_${LIVE_TURING_PRIMARY_KEY}/ /tmp/live_${LIVE_TURING_PRIMARY_KEY}
    sleep 5
done
```

#### Step 3: copy current classification to a remote website

```
HTML_TURING_OUTPUT=/tmp/shared-turing-dmf/live_${LIVE_TURING_PRIMARY_KEY}/html_files
REMOTE_WEBSITE_PATH=/tmp/remote-website
for EXT in css eot ttf woff woff2; do
    scp ${TURING_HOST_USER}@${TURING_HOST}:${HTML_TURING_OUTPUT}/*.${EXT} ${REMOTE_WEBSITE_HOST_USER}@${REMOTE_WEBSITE_HOST}:${REMOTE_WEBSITE_PATH}
done
ssh -t ${TURING_HOST_USER}@${TURING_HOST} "tail -n 0 -f ${HTML_TURING_OUTPUT}/watch.txt" | while read -r LINE; do
    scp ${TURING_HOST_USER}@${TURING_HOST}:${HTML_TURING_OUTPUT}/latest.html ${REMOTE_WEBSITE_HOST_USER}@${REMOTE_WEBSITE_HOST}:${REMOTE_WEBSITE_PATH}/index.html
done
```
