from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

def generate_pdf(result):
    # Create a new PDF object
    c = canvas.Canvas("../Book.pdf", pagesize=letter)
    
    for i, page_content in enumerate(result, start=1):
        text = page_content['content']
        image_url = page_content['imageurl']
        
        if text == '':
            # Save and close the PDF
            c.save()
            return

        img = ImageReader(image_url)
        # Draw the custom content on the PDF
        c.setFont("Helvetica", 11)
        lines = text.split("\n")
        # Set the line height
        line_height = 12

        # Set the margin
        margin = 50

        # Loop through the lines and draw them on the canvas
        y = letter[1] - margin
        for line in lines:
            # Split the line into words
            words = line.split()

            # Start with an empty line
            line_text = ""

            # Loop through the words and add them to the line until it's too long
            for word in words:
                if c.stringWidth(line_text + " " + word) < letter[0] - (2 * margin):
                    line_text += " " + word
                else:
                    # Check if there is enough space on the current page for the next line
                    if y - line_height < margin:
                        # If there isn't enough space, create a new page
                        c.showPage()
                        y = letter[1] - margin

                    # Draw the line on the canvas
                    c.drawString(margin, y, line_text.strip())

                    # Move to the next line
                    y -= line_height
                    line_text = ""

            # Draw any remaining text on the current page
            if line_text:
                # Check if there is enough space on the current page for the next line
                if y - line_height < margin:
                    # If there isn't enough space, create a new page
                    c.showPage()
                    y = letter[1] - margin

                # Draw the line on the canvas
                c.drawString(margin, y, line_text.strip())

                # Move to the next line
                y -= line_height
        # print("-------", y, margin, letter[0], letter[1])
        c.drawImage(img, 216, y-180, 180, 180)
        c.drawString(305, 10, f"{i}")

        if i != len(result):
            c.showPage()
    

