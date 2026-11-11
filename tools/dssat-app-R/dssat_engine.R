# ============================================================
#  Motor DSSAT en R base (sin dependencias de paquetes)
#  Leer/editar FileX, generar DSSBatch, correr CSM, leer Summary.
#  Espeja la lógica de la versión Python (tools/dssat-app).
# ============================================================

# ---- utilidades de columnas (ancho fijo, alineado al fin del token @) ----
.col_ends <- function(header) {
  m <- gregexpr("\\S+", header)[[1]]
  len <- attr(m, "match.length")
  as.integer(m + len - 2)        # índice 0-based del último caracter de cada token
}

.field_slice <- function(ends, i, line_len, last) {
  start <- if (i == 1) 0 else ends[i - 1] + 1
  stop  <- if (last) max(line_len, ends[i] + 1) else ends[i] + 1
  c(start = start, stop = stop)   # 0-based [start, stop)
}

# ---- lectura ----
fx_read <- function(path) {
  con <- file(path, encoding = "latin1")
  on.exit(close(con))
  readLines(con, warn = FALSE)
}

fx_write <- function(lines, path) {
  con <- file(path, encoding = "latin1")
  on.exit(close(con))
  writeLines(lines, con)
  invisible(path)
}

# localizar índices de líneas de datos de una sección + su header que contiene `col`
.locate <- function(lines, section, col) {
  sec_up <- toupper(section)
  in_sec <- FALSE; header_idx <- NA; data_idx <- integer(0)
  for (i in seq_along(lines)) {
    ln <- lines[i]
    if (substr(ln, 1, 1) == "*") {
      if (!is.na(header_idx)) break        # tabla hallada terminó
      nm <- toupper(trimws(substr(ln, 2, nchar(ln))))
      in_sec <- startsWith(nm, sec_up)
      next
    }
    if (!in_sec) next
    s <- trimws(ln)
    if (startsWith(s, "@")) {
      if (!is.na(header_idx)) break        # nueva tabla: la hallada terminó
      toks <- toupper(gsub("\\.+$","",strsplit(sub("^@", "", s), "\\s+")[[1]]))
      if (toupper(col) %in% toks) { header_idx <- i; data_idx <- integer(0) }
      next
    }
    if (!is.na(header_idx) && nchar(s) > 0 && !startsWith(s, "!"))
      data_idx <- c(data_idx, i)
  }
  if (is.na(header_idx)) stop(sprintf("No encontré columna '%s' en sección '%s'", col, section))
  list(header = header_idx, data = data_idx)
}

.col_index <- function(header, col) {
  toks <- gsub("\\.+$","",strsplit(sub("^\\s*@", "", header), "\\s+")[[1]])
  which(toupper(toks) == toupper(col))[1]
}

# leer una celda (por nivel = primera columna, o por fila)
fx_get <- function(lines, section, col, level = NULL, row = 1) {
  loc <- .locate(lines, section, col)
  header <- lines[loc$header]; ends <- .col_ends(header)
  ci <- .col_index(header, col); ncols <- length(strsplit(sub("^\\s*@","",header),"\\s+")[[1]])
  pos <- if (!is.null(level)) {
    lv <- vapply(loc$data, function(j) {
      sl <- .field_slice(ends, 1, nchar(lines[j]), ncols == 1)
      suppressWarnings(as.integer(trimws(substr(lines[j], sl["start"]+1, sl["stop"]))))
    }, integer(1))
    which(lv == level)[1]
  } else row
  li <- loc$data[pos]; ln <- lines[li]
  sl <- .field_slice(ends, ci, nchar(ln), ci == ncols)
  trimws(substr(ln, sl["start"] + 1, sl["stop"]))
}

# setear una celda preservando ancho (justificado a derecha; 'left' para texto ancho)
fx_set <- function(lines, section, col, value, level = NULL, row = 1, justify = "right") {
  loc <- .locate(lines, section, col)
  header <- lines[loc$header]; ends <- .col_ends(header)
  toks <- strsplit(sub("^\\s*@","",header),"\\s+")[[1]]; ncols <- length(toks)
  ci <- .col_index(header, col)
  rows <- loc$data
  pos <- if (!is.null(level)) {
    lv <- vapply(rows, function(j) {
      sl <- .field_slice(ends, 1, nchar(lines[j]), ncols == 1)
      suppressWarnings(as.integer(trimws(substr(lines[j], sl["start"]+1, sl["stop"]))))
    }, integer(1))
    which(lv == level)[1]
  } else row
  li <- rows[pos]; ln <- lines[li]
  last <- ci == ncols
  sl <- .field_slice(ends, ci, nchar(ln), last)
  start <- sl["start"]; stop <- sl["stop"]; width <- stop - start
  sval <- as.character(value)
  if (nchar(ln) < stop) ln <- paste0(ln, strrep(" ", stop - nchar(ln)))
  if (last) {
    newf <- if (justify == "left") sval else formatC(sval, width = width, flag = " ")
    lines[li] <- paste0(substr(ln, 1, start), newf)
  } else {
    if (nchar(sval) > width && justify == "left") {
      # texto ancho: extender hasta el inicio del token siguiente
      starts <- gregexpr("\\S+", header)[[1]]
      nxt <- starts[ci + 1] - 1
      field_txt <- substr(ln, start + 1, nxt)
      lead <- nchar(field_txt) - nchar(sub("^ +", "", field_txt))
      if (nchar(sval) > (nxt - start - lead)) lead <- 0
      body <- formatC(sval, width = -(nxt - start - lead), flag = "-")
      lines[li] <- paste0(substr(ln,1,start), strrep(" ",lead), body, substr(ln, nxt+1, nchar(ln)))
    } else {
      if (nchar(sval) > width) stop(sprintf("'%s' no entra en columna '%s' (ancho %d)", sval, col, width))
      newf <- if (justify=="left") formatC(sval,width=-width,flag="-") else formatC(sval,width=width)
      lines[li] <- paste0(substr(ln,1,start), newf, substr(ln, stop+1, nchar(ln)))
    }
  }
  lines
}

# setear col en TODAS las filas de TODAS las tablas de la sección que la tengan
fx_set_all <- function(lines, section, col, value, justify = "right") {
  sec_up <- toupper(section); in_sec <- FALSE; header <- NULL; ends <- NULL; ci <- NA; ncols <- NA
  for (i in seq_along(lines)) {
    ln <- lines[i]
    if (substr(ln,1,1) == "*") { in_sec <- startsWith(toupper(trimws(substr(ln,2,nchar(ln)))), sec_up); header <- NULL; next }
    if (!in_sec) next
    s <- trimws(ln)
    if (startsWith(s, "@")) {
      toks <- strsplit(sub("^@","",s),"\\s+")[[1]]
      if (toupper(col) %in% toupper(gsub("\\.+$","",toks))) { header <- ln; ends <- .col_ends(ln); ci <- which(toupper(gsub("\\.+$","",toks))==toupper(col))[1]; ncols <- length(toks) }
      else header <- NULL
      next
    }
    if (!is.null(header) && nchar(s)>0 && !startsWith(s,"!")) {
      last <- ci == ncols; sl <- .field_slice(ends, ci, nchar(ln), last)
      start <- sl["start"]; stop <- sl["stop"]; width <- stop-start; sval <- as.character(value)
      if (nchar(ln) < stop) ln <- paste0(ln, strrep(" ", stop-nchar(ln)))
      newf <- if (justify=="left") formatC(sval,width=-width,flag="-") else formatC(sval,width=width)
      lines[i] <- paste0(substr(ln,1,start), newf, substr(ln, stop+1, nchar(ln)))
    }
  }
  lines
}

# puntero de tratamiento (ej. nivel de PLANTING que usa el tratamiento trt)
fx_trt_pointer <- function(lines, trt, pointer) {
  as.integer(fx_get(lines, "TREATMENTS", pointer, level = trt))
}

# tratamientos (data.frame)
fx_treatments <- function(lines) {
  loc <- .locate(lines, "TREATMENTS", "N")
  header <- lines[loc$header]; ends <- .col_ends(header)
  toks <- strsplit(sub("^\\s*@","",header),"\\s+")[[1]]; ncols <- length(toks)
  do.call(rbind, lapply(loc$data, function(j) {
    ln <- lines[j]
    vals <- vapply(seq_len(ncols), function(i){ sl<-.field_slice(ends,i,nchar(ln),i==ncols); trimws(substr(ln,sl["start"]+1,sl["stop"])) }, character(1))
    setNames(as.data.frame(as.list(vals), stringsAsFactors=FALSE), toks)
  }))
}

# ---- batch ----
write_dssbatch <- function(path, filex, trtno = 1L, rp = 1L, sq = 0L) {
  name <- basename(filex)
  left <- formatC(name, width = -92, flag = "-")
  nums <- sprintf(" %6d %6d %6d %6d %6d", trtno, rp, sq, 0L, 0L)
  hdr <- c("$BATCH(RUN)", "!",
           paste0("@FILEX", strrep(" ", 86), "TRTNO     RP     SQ     OP     CO"))
  writeLines(c(hdr, paste0(left, nums)), path)
  invisible(path)
}

# ---- correr CSM ----
find_dscsm <- function(dssat_dir) {
  # dscsm048 (Linux/mac) o DSCSM048.EXE (Windows); NO .CTR/.v48/etc.
  cands <- list.files(dssat_dir,
    pattern = "^[Dd][Ss][Cc][Ss][Mm][0-9]+(\\.[Ee][Xx][Ee])?$", full.names = TRUE)
  if (length(cands) == 0) stop("No encontré el ejecutable DSCSM0XX en ", dssat_dir)
  cands[1]
}

run_dssat <- function(dssat_dir, model, mode, batch_file, work_dir) {
  exe <- find_dscsm(dssat_dir)
  old <- setwd(work_dir); on.exit(setwd(old))
  Sys.setenv(DSSAT_HOME = dssat_dir)
  status <- system2(exe, args = c(model, mode, basename(batch_file)),
                    stdout = TRUE, stderr = TRUE)
  rc <- attr(status, "status"); if (is.null(rc)) rc <- 0
  list(rc = rc, output = status)
}

# ---- leer Summary.OUT ----
read_summary <- function(path) {
  lines <- readLines(path, warn = FALSE)
  hi <- grep("^@", lines)[1]
  if (is.na(hi)) return(data.frame())
  header <- lines[hi]; ends <- .col_ends(header)
  toks <- strsplit(sub("^\\s*@","",header),"\\s+")[[1]]
  toks <- toks[toks != "@"]; ncols <- length(toks)
  drows <- c(); j <- hi + 1
  while (j <= length(lines)) {
    s <- lines[j]
    if (nchar(trimws(s)) == 0 || substr(s,1,1) %in% c("@","*")) break
    if (substr(s,1,1) != "!") drows <- c(drows, j)
    j <- j + 1
  }
  if (length(drows) == 0) return(data.frame())
  mat <- do.call(rbind, lapply(drows, function(k){
    ln <- lines[k]
    vapply(seq_len(ncols), function(i){ sl<-.field_slice(ends,i,nchar(ln),i==ncols); trimws(substr(ln,sl["start"]+1,sl["stop"])) }, character(1))
  }))
  df <- as.data.frame(mat, stringsAsFactors = FALSE); names(df) <- toks
  for (c in names(df)) { suppressWarnings({ n <- as.numeric(df[[c]]); if (!all(is.na(n))) df[[c]] <- n }) }
  df
}
