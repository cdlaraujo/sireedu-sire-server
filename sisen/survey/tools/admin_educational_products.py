# This script will be used to create connections between educational products and classes

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sisen.settings")
django.setup()

import pandas as pd
from django.db import IntegrityError
from colorama import Fore, Style, init
import argparse

from sisen.survey.models import (
    EducationalProduct,
    ClassProduct,
    Class
)

# Initialize colorama
init(autoreset=True)


class EducationalProductAdmin:
    def find_educational_products(self, **kwargs):
        """Find educational products matching the given arguments.
        
        Args:
            **kwargs: Filter criteria for educational products
            
        Returns:
            QuerySet of matching educational products
        """
        # If there is no argument, return all the educational products
        if not kwargs:
            return EducationalProduct.objects.all()

        # Use icontains for name for more flexible searching
        if 'name' in kwargs:
            name = kwargs.pop('name')
            return EducationalProduct.objects.filter(name__icontains=name, **kwargs)

        # If there are other arguments, filter the educational products
        return EducationalProduct.objects.filter(**kwargs)


class ClassAdmin:
    def find_class(self, **kwargs):
        """Find a single class matching the given arguments.
        
        Args:
            **kwargs: Filter criteria for classes
            
        Returns:
            The single matching class object
            
        Raises:
            ValueError: If zero or multiple matches are found
        """
        # Handle searching by description (more common) rather than "name"
        if 'name' in kwargs:
            name = kwargs.pop('name')
            classes = Class.objects.filter(description__icontains=name, **kwargs)
        else:
            classes = Class.objects.filter(**kwargs)

        if not classes.exists():
            raise ValueError(f"No class found matching: {kwargs}")

        if classes.count() > 1:
            matches = [f"{c.id}: {c.description} ({c.code} - {c.year}/{c.semester})" for c in classes]
            raise ValueError(
                f"Multiple classes match ({classes.count()}):\n"
                + "\n".join(matches)
            )

        return classes.first()


class AdminPanel:
    def __init__(self):
        self.educational_product_admin = EducationalProductAdmin()
        self.class_admin = ClassAdmin()

    def _select_product(self, products):
        """Let user select a product from a list of products."""
        if not products.exists():
            print(f"{Fore.YELLOW}No educational products found.")
            return None
            
        if products.count() == 1:
            product = products.first()
            print(f"{Fore.GREEN}Found one product: {product.name}")
            return product
            
        print(f"{Fore.CYAN}Educational products found:")
        for i, ep in enumerate(products, 1):
            print(f"{i}: {ep.id} - {ep.name} ({ep.type}, {ep.educational_code})")
            print(f"    {ep.info}")
            
        while True:
            try:
                selection = input(f"\nSelect product number (1-{products.count()}), 'all' for all or 'q' to quit: ")
                
                if selection.lower() == 'q':
                    return None
                    
                if selection.lower() == 'all':
                    return products.all()
                
                index = int(selection) - 1
                if 0 <= index < products.count():
                    return products[index]
                else:
                    print(f"{Fore.RED}Invalid selection. Please choose a number between 1 and {products.count()}.")
            except ValueError:
                print(f"{Fore.RED}Invalid input. Please enter a number.")

    def create_class_product(self):
        """Create a class product with the correct products and classes."""
        print(f"{Fore.CYAN}=== Create Class Product ===")
        
        # Get product search criteria
        kwargs = {}
        product_search = input("Product name to search (or press Enter for all products): ")
        product_code = input("Product code to search (or press Enter for all products): ")
        
        if product_search:
            kwargs["name"] = product_search
        if product_code:
            kwargs["educational_code__icontains"] = product_code

        # Find matching educational products
        educational_products = self.educational_product_admin.find_educational_products(**kwargs)
        
        # Let user select a product
        selected_products = self._select_product(educational_products)
        if not selected_products:
            print("Operation cancelled.")
            return
        
        # Handle both single product and multiple products cases
        products_to_process = []
        if hasattr(selected_products, 'all') and callable(getattr(selected_products, 'all')):  
            # It's a queryset (user selected 'all')
            products_to_process = list(selected_products)
            print(f"{Fore.GREEN}Selected {len(products_to_process)} products")
        else:
            # It's a single product
            products_to_process = [selected_products]
            print(f"{Fore.GREEN}Selected product: {selected_products.name} ({selected_products.type}, {selected_products.educational_code})")

        # Find the class with user-friendly retry loop
        selected_class = None
        while not selected_class:
            try:
                kwargs = {}
                class_search = input("Class description to search (or 'q' to quit): ")

                if class_search.lower() == "q":
                    print("Operation cancelled.")
                    return

                kwargs["name"] = class_search
                selected_class = self.class_admin.find_class(**kwargs)
                print(f"{Fore.GREEN}Found class: {selected_class.description} ({selected_class.code} - {selected_class.year}/{selected_class.semester})")
                
            except ValueError as e:
                print(f"{Fore.RED}{str(e)}")
                retry = input("Try again? (y/n): ").lower()
                if retry != "y":
                    return

        # Create the connection between the educational product(s) and the class
        success_count = 0
        existing_count = 0
        error_count = 0
        
        for product in products_to_process:
            try:
                # Check if this relationship already exists
                if ClassProduct.objects.filter(class_id=selected_class, product=product).exists():
                    print(f"{Fore.YELLOW}Product '{product.name}' is already assigned to this class.")
                    existing_count += 1
                    continue
                    
                class_product = ClassProduct.objects.create(
                    class_id=selected_class, 
                    product=product
                )
                print(f"{Fore.GREEN}Successfully created connection between class '{selected_class.description}' and product '{product.name}'")
                success_count += 1
                
            except IntegrityError:
                print(f"{Fore.YELLOW}Product '{product.name}' is already assigned to this class.")
                existing_count += 1
            except Exception as e:
                print(f"{Fore.RED}Error creating class product for '{product.name}': {e}")
                error_count += 1
        
        # Print summary
        if len(products_to_process) > 1:
            print(f"\n{Fore.CYAN}Summary:")
            print(f"{Fore.GREEN}Successfully connected: {success_count}")
            print(f"{Fore.YELLOW}Already connected: {existing_count}")
            if error_count > 0:
                print(f"{Fore.RED}Errors: {error_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Educational Product Admin Tool")
    parser.add_argument('--create', action='store_true', help="Create a new class product connection")
    
    args = parser.parse_args()
    admin_panel = AdminPanel()
    
    if args.create:
        admin_panel.create_class_product()
    else:
        # Default action if no arguments provided
        admin_panel.create_class_product()