.PHONY: build generate run

generate:
	pyside6-rcc ./apic_studio/resource/icons.qrc -o ./apic_studio/resource/resources.py

run:
	uv run src/apic_studio.py

build:
	uv run build.py


