# The release workflow picks the tag and creates the release on GitHub, so a
# release never depends on the state of a local checkout.
.PHONY: release
release: ## release main through the release workflow
	gh workflow run release --ref main
