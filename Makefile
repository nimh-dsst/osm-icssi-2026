# Makefile for OSM ICSSI 2026 (extended abstract + A0 poster)
#
# The poster shares the analysis data with the preprint/poster line of work.
# Its figures regenerate from the committed results/*_2024_2025.csv (no DuckDB
# needed). tectonic is taken from PATH; if the shared OSM venv is present its
# bin is prepended, otherwise a system/cloud install is used.

.PHONY: poster poster-figures clean help

OSM_VENV_BIN ?= $(HOME)/proj/osm/venv/bin
export PATH := $(OSM_VENV_BIN):$(PATH)

POSTER_DIR ?= latex-poster
POSTER_SRC ?= osm-icssi-2026-poster.tex
PYTHON ?= python

# Regenerate the poster figures from the in-repo results CSVs.
poster-figures:
	@echo "Regenerating poster figures from results/*_2024_2025.csv..."
	$(PYTHON) scripts/make_poster_figures.py

# Compile the A0 poster to PDF (tectonic handles biber internally).
poster: poster-figures
	@echo "Compiling poster (tectonic)..."
	cd $(POSTER_DIR) && tectonic -X compile $(POSTER_SRC)
	@echo "Poster generated: $(POSTER_DIR)/$(POSTER_SRC:.tex=.pdf)"

# Remove LaTeX auxiliary files.
clean:
	cd $(POSTER_DIR) && rm -f *.aux *.log *.out *.bbl *.blg *.bcf *.run.xml *.synctex.gz *.fls *.fdb_latexmk *.toc *.xdv

help:
	@echo "OSM ICSSI 2026 Makefile"
	@echo "  make poster-figures - Regenerate poster figures from results/*_2024_2025.csv"
	@echo "  make poster         - Regenerate figures and compile the A0 poster (tectonic)"
	@echo "  make clean          - Remove LaTeX auxiliary files"
