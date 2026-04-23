# Demo: Claude without mcp-stats-oracle

**Prompt (user):**
> Here are 252 AAPL daily closes for 2020 (values below). Is the series
> entering a new regime? Give me your confidence.
>
> `[75.09, 74.36, 74.95, ... , 134.87, 133.72]`

**Response (Claude with no tools):**

> Looking at the values you've shared, I can eyeball some movement — the
> series opens in the mid-70s, drops into the high 50s, and closes well
> above $130. That looks like a large year-long move. Whether it constitutes
> a "new regime" depends on what "regime" means here — a level shift, a
> volatility shift, or a structural break in the data-generating process?
>
> Without being able to run the actual statistics, my options are limited
> to qualitative observation. What I'd want to do is:
>
> - Compute rolling standard deviation of log returns
> - Fit a GARCH or Markov-switching model
> - Run a Bayesian changepoint detector with calibrated hazard rate
> - Look at the return distribution pre- and post- suspected break
>
> My confidence based purely on eyeballing a list: maybe 70% that the
> series has multiple regimes, but I cannot tell you when they transitioned
> or how severe the volatility shift was without actually computing the
> statistics.

**Problem:** no numbers, no changepoint dates, no confidence interval.
Claude correctly names the right techniques but cannot run any of them.
