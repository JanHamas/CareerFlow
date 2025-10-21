

async def handle_checkboxes(self, question_ele, response, responses_index):
    """
    Handles checkbox questions where one or more options can be selected.

    Parameters:
        question_ele (Locator/ElementHandle): The container element for the question.
        response (str | list): AI or user response, e.g. "Java, C, Python" or ["Java", "C", "Python"].
        responses_index (int): Question index for logging.
    """
    try:
        # --- Normalize responses into a clean lowercase list ---
        if isinstance(response, str):
            response_list = re.split(r',| and ', response)
            response_list = [r.strip().lower() for r in response_list if r.strip()]
        else:
            logger.warning(f"Invalid response type for Q{responses_index + 1}: {type(response)}")
            return False

        if not response_list:
            logger.warning(f"No valid responses found for Q{responses_index + 1}")
            return False

        # --- Collect all checkboxes within this question element ---
        checkbox_inputs = await question_ele.query_selector_all("input[type='checkbox']")
        if not checkbox_inputs:
            return False

        found_any = False

        # --- Iterate and click matches ---
        for checkbox in checkbox_inputs:
            try:
                # Get parent label text
                label = await checkbox.query_selector("xpath=..")
                if not label:
                    continue

                label_text = (await label.inner_text()).strip().lower()

                for target in response_list:
                    # Allow partial matches (e.g., "contract" in "contract-to-hire")
                    if target in label_text:
                        # ✅ Check if already selected
                        is_checked = await checkbox.is_checked()
                        if not is_checked:
                            await label.click()
                            logger.info(f"✓ Checked: '{label_text}' (Q{responses_index + 1})")
                        else:
                            logger.info(f"⚪ Already checked: '{label_text}' (Q{responses_index + 1})")

                        found_any = True
                        break

            except Exception as e:
                logger.warning(f"Checkbox selection error (Q{responses_index + 1}): {e}")

        if not found_any:
            logger.warning(f"No matching checkboxes clicked for Q{responses_index + 1}")
            return False

        return True