#' Append a provenance event to a JSONL ledger
#'
#' @param path Path to the ledger file.
#' @param event_type Short event class, e.g. "model_call" or "tool_call".
#' @param payload Named list containing event-specific data.
#' @param run_id Optional workflow/run identifier.
#' @param model Optional model identifier.
#' @param tool Optional tool/function identifier.
#' @return The record invisibly.
#' @export
ragent_append <- function(path, event_type, payload = list(), run_id = NULL,
                          model = NULL, tool = NULL) {
  stopifnot(is.character(path), length(path) == 1L, nzchar(path))
  stopifnot(is.character(event_type), length(event_type) == 1L, nzchar(event_type))
  stopifnot(is.list(payload))

  previous_hash <- ""
  if (file.exists(path)) {
    lines <- readLines(path, warn = FALSE, encoding = "UTF-8")
    if (length(lines)) {
      last <- jsonlite::fromJSON(lines[[length(lines)]], simplifyVector = FALSE)
      previous_hash <- last$event_hash %||% ""
    }
  }

  record <- list(
    schema_version = 1L,
    timestamp_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%OS3Z", tz = "UTC"),
    event_type = event_type,
    run_id = run_id,
    model = model,
    tool = tool,
    payload = payload,
    previous_hash = previous_hash
  )
  record$event_hash <- .ragent_hash(record)

  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  cat(.ragent_json(record), "\n", file = path, append = TRUE, sep = "")
  invisible(record)
}

#' Verify a provenance ledger
#'
#' @param path Path to a JSONL ledger.
#' @return A list with `valid`, `records`, and `first_error`.
#' @export
ragent_verify <- function(path) {
  if (!file.exists(path)) {
    return(list(valid = TRUE, records = 0L, first_error = NA_integer_))
  }

  lines <- readLines(path, warn = FALSE, encoding = "UTF-8")
  expected_previous <- ""

  for (i in seq_along(lines)) {
    parsed <- tryCatch(
      jsonlite::fromJSON(lines[[i]], simplifyVector = FALSE),
      error = function(e) NULL
    )
    if (!is.list(parsed) || is.null(parsed$event_hash)) {
      return(list(valid = FALSE, records = length(lines), first_error = i))
    }

    observed <- parsed$event_hash
    parsed$event_hash <- NULL

    if (!identical(parsed$previous_hash %||% "", expected_previous) ||
        !identical(.ragent_hash(parsed), observed)) {
      return(list(valid = FALSE, records = length(lines), first_error = i))
    }
    expected_previous <- observed
  }

  list(valid = TRUE, records = length(lines), first_error = NA_integer_)
}

.ragent_json <- function(x) {
  jsonlite::toJSON(
    x,
    auto_unbox = TRUE,
    null = "null",
    na = "null",
    digits = NA,
    pretty = FALSE
  )
}

.ragent_hash <- function(x) {
  digest::digest(.ragent_json(x), algo = "sha256", serialize = FALSE)
}

`%||%` <- function(x, y) if (is.null(x)) y else x
