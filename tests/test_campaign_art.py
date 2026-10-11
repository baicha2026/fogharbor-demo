from adventure import campaign, campaign_art


def test_campaign_art_exports_non_empty_png_assets() -> None:
    game = campaign.new_game()

    assert campaign_art.map_image(game).startswith(b"\x89PNG\r\n\x1a\n")
    assert campaign_art.portrait("hero").startswith(b"\x89PNG\r\n\x1a\n")
    assert campaign_art.book_icon("ember_arc").startswith(b"\x89PNG\r\n\x1a\n")


def test_campaign_art_supports_every_enemy_behavior() -> None:
    for behavior in campaign_art.ENEMY_SPRITES:
        image = campaign_art.enemy_portrait({"behavior": behavior})
        assert image.startswith(b"\x89PNG\r\n\x1a\n")

