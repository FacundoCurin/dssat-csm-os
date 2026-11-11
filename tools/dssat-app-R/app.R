# ============================================================
#  Generador de manejos DSSAT — Shiny app (R nativo)
#  Solo requiere: DSSAT instalado + el paquete 'shiny'.
#  Correr:  shiny::runApp()   (o usar run_shiny.bat / run_shiny.sh)
# ============================================================
library(shiny)
source("dssat_engine.R")

CROP_DIR   <- c(maiz = "Maize", trigo = "Wheat", soja = "Soybean")
CROP_EXT   <- c(maiz = "MZX",   trigo = "WHX",   soja = "SBX")
CROP_MODEL <- list(maiz = c("MZCER048","MZIXM048"), trigo = c("WHCER048","WHAPS048"),
                   soja = c("CRGRO048"))

# factores de manejo: etiqueta -> cómo se aplica al FileX
FACTORS <- list(
  pdate  = list(label = "Fecha de siembra (YYDDD)", section="PLANTING DETAILS", col="PDATE", ptr="MP"),
  ppop   = list(label = "Densidad (pl/m2)",          section="PLANTING DETAILS", col="PPOP", ptr="MP", also="PPOE"),
  ingeno = list(label = "Cultivar (INGENO)",         section="CULTIVARS",        col="INGENO", ptr="CU"),
  famn   = list(label = "N a la siembra (kg/ha)",    section="FERTILIZERS",      col="FAMN", ptr="MF")
)

detect_dssat <- function() {
  env <- Sys.getenv("DSSAT_HOME")
  if (nzchar(env) && dir.exists(env)) return(env)
  cand <- c(file.path(path.expand("~"),"dssathome"),
            "C:/DSSAT48","C:/DSSAT47","C:/DSSAT49","D:/DSSAT48",
            "/opt/dssat", file.path(path.expand("~"),"DSSAT48"))
  for (c in cand) if (dir.exists(c) &&
      length(list.files(c, pattern="^[Dd][Ss][Cc][Ss][Mm][0-9]+")) > 0) return(c)
  if (nzchar(env)) env else file.path(path.expand("~"),"dssathome")
}

ui <- fluidPage(
  titlePanel("🌱 Generador de manejos DSSAT"),
  sidebarLayout(
    sidebarPanel(width = 4,
      h4("1 · Modelo y datos"),
      textInput("dssat", "Carpeta DSSAT", value = detect_dssat()),
      selectInput("crop", "Cultivo", choices = c("Maíz"="maiz","Trigo"="trigo","Soja"="soja")),
      uiOutput("model_ui"), uiOutput("exp_ui"),
      h4("2 · Condiciones"),
      checkboxInput("secano", "Secano (sin riego)", TRUE),
      checkboxInput("nnolim", "N no limitante", FALSE),
      numericInput("nyers", "Años a simular", 1, 1, 60),
      sliderInput("sh2o", "Humedad inicial (cm3/cm3)", 0.05, 0.40, 0.26, 0.01),
      h4("3 · Manejos a comparar"),
      checkboxGroupInput("factors", NULL,
        choices = setNames(names(FACTORS), vapply(FACTORS, `[[`, "", "label"))),
      uiOutput("levels_ui"),
      actionButton("run", "▶ Generar y correr", class = "btn-primary")
    ),
    mainPanel(width = 8,
      h4("Tratamientos"), tableOutput("trts"),
      h4("Resultados"), textOutput("status"),
      plotOutput("plot", height = "320px"),
      tableOutput("results"), downloadButton("dl", "Descargar CSV")
    )
  )
)

server <- function(input, output, session) {
  output$model_ui <- renderUI(selectInput("model","Modelo", CROP_MODEL[[input$crop]]))
  exps <- reactive({
    d <- file.path(input$dssat, CROP_DIR[[input$crop]])
    if (!dir.exists(d)) return(character(0))
    list.files(d, pattern = paste0("\\.", CROP_EXT[[input$crop]], "$"), ignore.case = TRUE)
  })
  output$exp_ui <- renderUI(selectInput("exp","Experimento", exps()))

  base_fx <- reactive({
    req(input$exp)
    fx_read(file.path(input$dssat, CROP_DIR[[input$crop]], input$exp))
  })
  output$trts <- renderTable({ req(base_fx()); head(fx_treatments(base_fx())[, c("N","CU","MP","MF")], 10) })

  output$levels_ui <- renderUI({
    lapply(input$factors, function(k){
      cur <- tryCatch(fx_get(base_fx(), FACTORS[[k]]$section, FACTORS[[k]]$col, level=1), error=function(e) "")
      textInput(paste0("lv_", k), paste0(FACTORS[[k]]$label, " (actual: ", cur, ")"), value = cur)
    })
  })

  results <- eventReactive(input$run, {
    fx <- base_fx(); trt <- 1L
    # niveles por factor
    levs <- list()
    for (k in input$factors) {
      v <- trimws(strsplit(input[[paste0("lv_", k)]], ",")[[1]])
      v <- v[nzchar(v)]; if (length(v)) levs[[k]] <- v
    }
    if (!length(levs)) levs <- list(.none = "x")
    combos <- expand.grid(levs, stringsAsFactors = FALSE)
    work <- file.path(tempdir(), paste0("dssatrun_", as.integer(Sys.time()))); dir.create(work, showWarnings=FALSE)
    # fecha de inicio común si se barre pdate
    sdate_base <- tryCatch(as.integer(fx_get(fx,"SIMULATION CONTROLS","SDATE",level=1)), error=function(e) NA)
    pdates <- if ("pdate" %in% names(levs)) suppressWarnings(as.integer(levs$pdate)) else integer(0)
    target_sdate <- if (length(pdates)) min(c(pdates, if(!is.na(sdate_base)) sdate_base)) else NA

    rows <- list()
    withProgress(message = "Corriendo DSSAT…", value = 0, {
      for (r in seq_len(nrow(combos))) {
        f2 <- fx
        for (k in names(levs)) if (k != ".none") {
          lvl <- fx_trt_pointer(fx, trt, FACTORS[[k]]$ptr)
          f2 <- fx_set(f2, FACTORS[[k]]$section, FACTORS[[k]]$col, combos[r,k], level = lvl)
          if (!is.null(FACTORS[[k]]$also))
            f2 <- fx_set(f2, FACTORS[[k]]$section, FACTORS[[k]]$also, combos[r,k], level = lvl)
        }
        if (!is.na(target_sdate)) {
          f2 <- fx_set_all(f2, "SIMULATION CONTROLS", "SDATE", sprintf("%05d", target_sdate))
          f2 <- fx_set(f2, "INITIAL CONDITIONS", "ICDAT", sprintf("%05d", target_sdate), level=1)
        }
        f2 <- fx_set_all(f2, "SIMULATION CONTROLS", "IRRIG", if (input$secano) "N" else "R")
        f2 <- fx_set_all(f2, "SIMULATION CONTROLS", "NITRO", if (input$nnolim) "N" else "Y")
        f2 <- fx_set_all(f2, "SIMULATION CONTROLS", "NYERS", input$nyers)
        f2 <- fx_set_all(f2, "INITIAL CONDITIONS", "SH2O", input$sh2o)
        f2 <- fx_set_all(f2, "SIMULATION CONTROLS", "SUMRY", "Y")
        f2 <- fx_set_all(f2, "SIMULATION CONTROLS", "FNAME", "N")
        nm <- sprintf("SWP%05d.%s", r, CROP_EXT[[input$crop]]); fx_write(f2, file.path(work, nm))
        write_dssbatch(file.path(work,"DSSBatch.v48"), file.path(work,nm), trtno = trt)
        unlink(file.path(work,"Summary.OUT"))
        run_dssat(input$dssat, input$model, "N", file.path(work,"DSSBatch.v48"), work)
        s <- file.path(work,"Summary.OUT")
        rec <- as.list(combos[r, , drop=FALSE])
        if (file.exists(s)) {
          d <- read_summary(s)
          if (input$nyers > 1) { rec$HWAM <- round(mean(d$HWAM[d$HWAM>=0], na.rm=TRUE)) }
          else { rec$HWAM <- d$HWAM[1]; rec$MDAT <- d$MDAT[1]; rec$PRCP <- d$PRCP[1] }
        } else rec$HWAM <- NA
        rows[[r]] <- as.data.frame(rec, stringsAsFactors = FALSE)
        incProgress(1/nrow(combos))
      }
    })
    do.call(rbind, rows)
  })

  output$status  <- renderText({ req(results()); sprintf("%d corridas.", nrow(results())) })
  output$results <- renderTable({ results() })
  output$plot <- renderPlot({
    df <- results(); req(df); fk <- setdiff(names(df), c("HWAM","MDAT","PRCP",".none"))
    if (length(fk) >= 1 && "HWAM" %in% names(df)) {
      x <- df[[fk[1]]]
      plot(factor(x), df$HWAM, type="o", xlab = FACTORS[[fk[1]]]$label, ylab = "HWAM (kg/ha)",
           main = "Respuesta simulada", pch=19)
      if (is.numeric(suppressWarnings(as.numeric(x))))
        lines(seq_along(x), df$HWAM, type="o", pch=19, col="darkgreen")
    }
  })
  output$dl <- downloadHandler(
    filename = function() "manejos_resultados.csv",
    content  = function(file) write.csv(results(), file, row.names = FALSE)
  )
}

shinyApp(ui, server)
