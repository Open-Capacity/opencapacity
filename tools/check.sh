#!/bin/sh
# Regenerates the examples, converts the YAML to JSON, and checks the specification.
# Needs python3, a JDK (JAVA_HOME), and the Jackson YAML jars in the local Maven repository.
# To get the jars: mvn dependency:get -Dartifact=com.fasterxml.jackson.dataformat:jackson-dataformat-yaml:2.21.8
set -e
cd "$(dirname "$0")/.."
M="$HOME/.m2/repository"
CP=$(ls "$M"/com/fasterxml/jackson/core/jackson-core/2.21.*/jackson-core-*.jar "$M"/com/fasterxml/jackson/core/jackson-databind/2.21.*/jackson-databind-*.jar "$M"/com/fasterxml/jackson/core/jackson-annotations/2.2*/jackson-annotations-*.jar "$M"/com/fasterxml/jackson/dataformat/jackson-dataformat-yaml/2.21.8/*.jar "$M"/org/yaml/snakeyaml/2.5/*.jar | grep -v sources | grep -v javadoc | tr '\n' ':')
python3 tools/examples.py
"${JAVA_HOME:-/usr}/bin/java" -cp "$CP" tools/Y2J.java "$PWD/opencapacity-1.0.yaml" "$PWD/opencapacity-1.0.json"
python3 tools/check.py opencapacity-1.0.json
