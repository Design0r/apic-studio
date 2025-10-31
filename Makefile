.PHONY: build generate run profile

generate:
	pyside6-rcc ./src/apic_studio/resources/icons.qrc -o ./src/apic_studio/resources/resources.py

run:
	uv run src/apic_studio.py

build:
	cd src/apic_studio_utils && uv run maturin build --release
	uv run build.py

plot:
	uv run pyreverse -S -o html --colorized -f ALL -p apic-studio  ./src/apic_studio

profile:
	uv run src/apic_studio_profile.py

snakeviz:
	uv run snakeviz apic_studio.prof

nuitka:
	uv run nuitka src/apic_studio.py --onefile --enable-plugin=pyside6
