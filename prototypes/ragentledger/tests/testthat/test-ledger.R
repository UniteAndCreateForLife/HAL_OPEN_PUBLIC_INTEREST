test_that("records are hash-linked and verify cleanly", {
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

  expect_equal(second$previous_hash, first$event_hash)

  result <- ragent_verify(path)
  expect_true(result$valid)
  expect_equal(result$records, 2L)
})

test_that("verification detects payload edits", {
  path <- tempfile(fileext = ".jsonl")
  ragent_append(path, "model_call", payload = list(value = 1))

  lines <- readLines(path, warn = FALSE)
  lines[[1]] <- sub('"value":1', '"value":2', lines[[1]], fixed = TRUE)
  writeLines(lines, path)

  result <- ragent_verify(path)
  expect_false(result$valid)
  expect_equal(result$first_error, 1L)
})
