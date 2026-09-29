source("R/ledger.R")

path <- tempfile(fileext = ".jsonl")
first <- ragent_append(
  path,
  "model_call",
  payload = list(prompt_sha256 = "example"),
  run_id = "run-1",
  model = "example-model"
)
second <- ragent_append(
  path,
  "tool_call",
  payload = list(args = list(query = "example")),
  run_id = "run-1",
  tool = "search"
)

stopifnot(identical(second$previous_hash, first$event_hash))
ok <- ragent_verify(path)
stopifnot(isTRUE(ok$valid), identical(ok$records, 2L))

lines <- readLines(path, warn = FALSE)
lines[[1]] <- sub('"prompt_sha256":"example"', '"prompt_sha256":"changed"', lines[[1]], fixed = TRUE)
writeLines(lines, path)

bad <- ragent_verify(path)
stopifnot(identical(bad$valid, FALSE), identical(bad$first_error, 1L))

cat("ragentledger smoke: PASS\n")
