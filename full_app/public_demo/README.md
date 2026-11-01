# Creator Decision Intelligence · Public Demo

This is a **fully synthetic** interactive portfolio demonstration of the decision workflow, not the live AI research engine.

## Run locally

```bash
pip install -r public_demo/requirements.txt
streamlit run public_demo/app.py
```

- No API key, Google account, Hermes, YouTube, Docker, or personal channel data required.
- Uses only `public_demo/demo_data.json` (deliberately fictional). **Do not interpret numbers, comments, market outcomes or recommendations as real.**
- Sections: channel snapshot, independently ranked A/B topic decisions, **absolute comment counts + illustrative content categories**, and decision-to-outcome record.
- Selected topic is held only in Streamlit's session state; **the demo does not persist data**.
- The full local application can access public YouTube data and call models, after configured by the owner.

## Deploy to Streamlit Community Cloud

1. Push source (without `.env`, local `data/`, or Desktop strategy records) to GitHub.
2. In Streamlit Community Cloud choose the repository and set entrypoint to **`public_demo/app.py`**.
3. The demo's requirements are in `public_demo/requirements.txt`. If deploying a demo-only repository, put `requirements.txt`, `app.py`, and `demo_data.json` in its root and use `app.py` as entrypoint.
4. Confirm the "synthetic demo" warning is always visible.

## What a reviewer should **not** infer

Synthetic examples do not demonstrate actual retrieval accuracy, model quality, lift in views, or prediction calibration. Comment count is not a proven predictor of product sales. The live local application still needs real environment integration tests.
