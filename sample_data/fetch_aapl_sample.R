# Fetch AAPL daily OHLCV from Yahoo Finance via quantmod and write a small
# CSV sample the plugin can reason over. Yahoo Finance data is freely
# redistributable for educational/demo purposes.
#
# Run: Rscript sample_data/fetch_aapl_sample.R

suppressPackageStartupMessages(library(quantmod))

from <- as.Date("2020-01-02")
to   <- as.Date("2020-12-31")

message(sprintf("Fetching AAPL daily OHLCV from Yahoo Finance (%s to %s) ...", from, to))
sym <- "AAPL"
env <- new.env()
getSymbols(sym, src = "yahoo", from = from, to = to, env = env, auto.assign = TRUE)
x <- env[[sym]]

df <- data.frame(
  date   = as.Date(index(x)),
  open   = as.numeric(x[, paste0(sym, ".Open")]),
  high   = as.numeric(x[, paste0(sym, ".High")]),
  low    = as.numeric(x[, paste0(sym, ".Low")]),
  close  = as.numeric(x[, paste0(sym, ".Close")]),
  volume = as.numeric(x[, paste0(sym, ".Volume")])
)

out <- file.path("sample_data", "aapl_2020.csv")
write.csv(df, out, row.names = FALSE)
cat(sprintf("Wrote %s (%d rows, %s to %s)\n",
            out, nrow(df), min(df$date), max(df$date)))
