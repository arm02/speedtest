import speedtest

st = speedtest.Speedtest()

print("Testing Download Speed...")
download = st.download() / 1_000_000  # convert to Mbps
print(f"Download Speed: {download:.2f} Mbps")

print("Testing Upload Speed...")
upload = st.upload() / 1_000_000  # convert to Mbps
print(f"Upload Speed: {upload:.2f} Mbps")

print("Ping:", st.results.ping)
