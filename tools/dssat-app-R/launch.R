# Lanzador: instala 'shiny' si falta y abre la app en el navegador.
# Se invoca con:  Rscript launch.R   (desde run_shiny.bat / run_shiny.sh)
args <- commandArgs(trailingOnly = FALSE)
fa <- grep("^--file=", args, value = TRUE)
if (length(fa) == 1) {
  here <- dirname(sub("^--file=", "", fa))
  if (nzchar(here)) setwd(here)
}

repo <- "https://cloud.r-project.org"
if (!requireNamespace("shiny", quietly = TRUE)) {
  message("Instalando 'shiny' (solo la primera vez)…")
  install.packages("shiny", repos = repo)
}
port <- as.integer(Sys.getenv("DSSAT_APP_PORT", "8080"))
message("Abriendo la app en http://localhost:", port, " …")
shiny::runApp(".", launch.browser = TRUE, port = port, host = "127.0.0.1")
