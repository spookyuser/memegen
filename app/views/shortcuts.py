from urllib.parse import parse_qs

from sanic import Blueprint, exceptions, response
from sanic.log import logger
from sanic.request import Request
from sanic_ext import openapi

from .. import models, settings, utils

blueprint = Blueprint("Shortcuts", url_prefix="/")


async def _generate_ai_meme(request: Request, query: str):
    """
    AI-powered meme generation that returns HTML with OpenGraph tags.
    When shared on social media (WhatsApp, Twitter, etc.), the preview will show the generated meme.
    """
    # Decode and clean up the query
    query_cleaned = query.strip().replace("-", " ").replace("_", " ")

    # Use the existing search functionality to find the best matching meme
    logger.info(f"AI meme request: {query_cleaned!r}")
    safe = utils.urls.flag(request, "safe", True)
    results = await utils.meta.search(request, query_cleaned, safe)

    if not results:
        logger.warning(f"No results found for: {query_cleaned!r}")
        return response.html(
            _generate_error_html(f"No meme found for: {query_cleaned}"),
            status=404
        )

    # Get the top result
    result = results[0]
    meme_url = utils.urls.normalize(result["image_url"])
    generator = result.get("generator", "AI")
    confidence = result.get("confidence", 0)

    logger.info(f"Generated meme URL: {meme_url} ({generator=} {confidence=})")

    # Tokenize the URL if needed (handles authentication)
    meme_url, _updated = await utils.meta.tokenize(request, meme_url)

    # Generate HTML with OpenGraph tags
    html_content = _generate_og_html(query_cleaned, meme_url)

    return response.html(html_content)


def _generate_og_html(query: str, meme_url: str) -> str:
    """Generate HTML with OpenGraph meta tags for social media sharing."""

    # Escape HTML special characters in query
    query_escaped = (
        query.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

    title = f"{query_escaped} - Memegen"
    description = f"AI-generated meme: {query_escaped}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>

    <!-- OpenGraph meta tags for social media sharing -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{meme_url}">
    <meta property="og:image:width" content="600">
    <meta property="og:image:height" content="600">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{meme_url}">

    <!-- Twitter Card meta tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{meme_url}">

    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}

        .container {{
            max-width: 800px;
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }}

        h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 24px;
        }}

        .query {{
            color: #667eea;
            font-size: 18px;
            margin-bottom: 20px;
            font-style: italic;
        }}

        img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .footer {{
            margin-top: 20px;
            color: #666;
            font-size: 14px;
        }}

        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}

        .footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AI-Generated Meme</h1>
        <p class="query">"{query_escaped}"</p>
        <img src="{meme_url}" alt="{query_escaped}">
        <div class="footer">
            Powered by <a href="{settings.BASE_URL}">Memegen.link</a>
        </div>
    </div>
</body>
</html>"""

    return html


def _generate_error_html(error_message: str) -> str:
    """Generate HTML for error pages."""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - Memegen</title>

    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .container {{
            max-width: 600px;
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }}

        h1 {{
            color: #e74c3c;
            margin-bottom: 20px;
        }}

        p {{
            color: #666;
            font-size: 16px;
        }}

        .footer {{
            margin-top: 20px;
            color: #666;
            font-size: 14px;
        }}

        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Oops!</h1>
        <p>{error_message}</p>
        <div class="footer">
            Go back to <a href="{settings.BASE_URL}">Memegen.link</a>
        </div>
    </div>
</body>
</html>"""

    return html


@blueprint.get(r"/images/<template_id:[^.]+>")
@openapi.summary("Redirect to an example image")
@openapi.parameter("template_id", str, "path", description="ID of a meme template")
@openapi.response(
    302, {"image/*": bytes}, "Successfully redirected to an example image"
)
@openapi.response(404, {"text/html": str}, "Template not found")
@openapi.response(501, {"text/html": str}, "Template not fully implemented")
async def example_path(request, template_id):
    template_id = utils.urls.clean(template_id)

    if settings.DEBUG:
        template = models.Template.objects.get_or_create(template_id)
    else:
        template = models.Template.objects.get_or_none(template_id)

    if template and template.valid:
        url = template.build_example_url(request, external=False)
        if settings.DEBUG:
            url = url.removesuffix(".png")
        return response.redirect(url)

    if settings.DEBUG:
        if "<" in template_id:
            message = f"Replace {template_id!r} in the URL"
        else:
            message = f"Template not fully implemented: {template}"
            logger.warning(message)
            template.datafile.save()
        raise exceptions.SanicException(message, 501)

    raise exceptions.NotFound(f"Template not found: {template_id}")


@blueprint.get(r"/<template_id:.+\.\w+>")
@openapi.summary("Redirect to an example image")
@openapi.parameter("template_id", str, "path", description="ID of a meme template")
@openapi.response(
    302, {"image/*": bytes}, "Successfully redirected to an example image"
)
@openapi.response(404, {"text/html": str}, "Template not found")
async def legacy_example_image(request, template_id):
    template_id, extension = template_id.rsplit(".", 1)
    template = models.Template.objects.get_or_none(template_id)
    if template:
        url = template.build_example_url(request, extension=extension, external=False)
        return response.redirect(url)
    raise exceptions.NotFound(f"Template not found: {template_id}")


@blueprint.get("/<template_id:slug>")
@openapi.summary("Redirect to an example image or generate AI meme")
@openapi.parameter("template_id", str, "path", description="ID of a meme template or natural language query")
@openapi.response(
    302, {"image/*": bytes}, "Successfully redirected to an example image"
)
@openapi.response(
    200, {"text/html": str}, "AI-generated meme page with OpenGraph tags"
)
@openapi.response(404, {"text/html": str}, "No matching template or meme found")
async def legacy_example_path(request, template_id):
    template_id_clean = template_id.strip("/")

    # First, check if this is a valid template
    template = models.Template.objects.get_or_none(template_id_clean)
    if template:
        return response.redirect(f"/images/{template_id_clean}")

    # If not a template and AI is enabled, try AI meme generation
    if settings.REMOTE_TRACKING_URL:
        return await _generate_ai_meme(request, template_id_clean)

    # Fall back to original redirect if no AI available
    return response.redirect(f"/images/{template_id_clean}")


@blueprint.get(r"/images/<template_id:slug>/<text_paths:[^/].*>")
@openapi.summary("Redirect to a custom image")
@openapi.parameter(
    "text_paths", str, "path", description="Lines of text: `<line1>/<line2>`"
)
@openapi.parameter("template_id", str, "path", description="ID of a meme template")
@openapi.response(302, {"image/*": bytes}, "Successfully redirected to a custom image")
async def custom_path(request, template_id, text_paths):
    if template_id == "images":
        return response.redirect(f"/images/{text_paths}".removesuffix("/"))

    params = {}
    text_paths = utils.urls.clean(text_paths)
    if "&" in text_paths:
        logger.warning(f"Fixing query string: {text_paths}")
        text_paths, query_string = text_paths.split("&", 1)
        params = parse_qs(query_string)
    elif "//" in text_paths:
        logger.warning(f"Truncating path: {text_paths}")
        text_paths = text_paths.split("//")[0]
    elif text_paths.endswith("/"):
        logger.warning(f"Fixing trailing slash: {text_paths}")
        text_paths = text_paths.rstrip("/")
    elif text_paths.endswith('"'):
        logger.warning(f"Fixing trailing quote: {text_paths}")
        text_paths = text_paths.rstrip('"')

    if text_paths.startswith("."):
        return response.redirect(
            request.app.url_for(
                "Images.detail_blank",
                template_filename=f"{template_id}{text_paths}",
            )
        )

    try:
        url = request.app.url_for(
            "Images.detail_text",
            template_id=template_id,
            text_filepath=text_paths,
            **params,
        )
    except exceptions.URLBuildError as e:
        if "text_filepath" in str(e):
            logger.warning(f"Handing missing extension: {e}")
        else:
            raise
        url = request.app.url_for(
            "Images.detail_text",
            template_id=template_id,
            text_filepath=text_paths + settings.DEFAULT_SUFFIX,
            **params,
        )

    if not settings.DEBUG:
        return response.redirect(url)

    template = models.Template.objects.get_or_create(template_id)
    template.datafile.save()
    animated = utils.urls.flag(request, "animated")
    extension = (
        settings.DEFAULT_ANIMATED_EXTENSION
        if animated
        else settings.DEFAULT_STATIC_EXTENSION
    )
    content = utils.html.gallery(
        [f"/images/{template_id}/{text_paths}.{extension}"],
        columns=False,
        refresh=30 if animated else 3,
        query_string=request.query_string,
    )
    return response.html(content)


@blueprint.get(r"/<template_id:(?!templates)[a-z-]+>/<text_paths:[^/].*\.\w+>")
@openapi.summary("Redirect to a custom image")
@openapi.parameter(
    "text_paths", str, "path", description="Lines of text: `<line1>/<line2>`"
)
@openapi.parameter("template_id", str, "path", description="ID of a meme template")
@openapi.response(302, {"image/*": bytes}, "Successfully redirected to a custom image")
@openapi.response(404, {"text/html": str}, description="Template not found")
async def legacy_custom_image(request, template_id, text_paths):
    text_paths, extension = text_paths.rsplit(".", 1)
    template = models.Template.objects.get_or_none(template_id)
    if template:
        url = request.app.url_for(
            "Images.detail_text",
            template_id=template_id,
            text_filepath=text_paths + "." + extension,
        )
        return response.redirect(url)
    raise exceptions.NotFound(f"Template not found: {template_id}")


@blueprint.get(r"/<template_id:(?!templates)[a-z-]+>/<text_paths:[^/].*>")
@openapi.summary("Redirect to a custom image")
@openapi.parameter(
    "text_paths", str, "path", description="Lines of text: `<line1>/<line2>`"
)
@openapi.parameter("template_id", str, "path", description="ID of a meme template")
@openapi.response(302, {"image/*": bytes}, "Successfully redirected to a custom image")
async def legacy_custom_path(request, template_id, text_paths):
    if template_id == "images":
        return response.redirect(f"/images/{text_paths}".removesuffix("/"))
    return response.redirect(f"/images/{template_id}/{text_paths}")
