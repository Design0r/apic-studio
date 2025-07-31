.PHONY: build generate run

generate:
	pyside6-rcc ./src/apic_studio/resources/icons.qrc -o ./src/apic_studio/resources/resources.py

run:
	uv run src/apic_studio.py

build:
	uv run build.py



plot:
	uv run pyreverse -S -o html --colorized -f ALL -p apic-studio  ./src/apic_studio