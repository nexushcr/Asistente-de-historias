# Adding Poppins Fonts

This README file explains how to add Poppins fonts and use them in your project with the Dockerfile.

## Step 1: Add Poppins Fonts

You can include Poppins fonts in your project by using Google Fonts. Add the following line in your HTML file:

```html
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap" rel="stylesheet">
```

Alternatively, you can download the Poppins font files and include them locally in your project.  Download them from [Google Fonts](https://fonts.google.com/specimen/Poppins).

## Step 2: Usage in CSS

After including the font, you can use it in your CSS as follows:

```css
body {
    font-family: 'Poppins', sans-serif;
}
```

## Step 3: Usage in Dockerfile

To incorporate Poppins fonts in your Docker image, you may want to avoid browser caching when your app makes an HTTP request. Below is an example to copy the font files into the image:

```Dockerfile
# Step to copy font files into the Docker image
COPY ./fonts /path/to/fonts
```

Make sure you replace `/path/to/fonts` with your desired destination.

## Conclusion

Following the above steps allows you to use Poppins fonts in your web application, and ensure they are included in your Docker image for use.